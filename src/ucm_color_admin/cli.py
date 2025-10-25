"""Command line interface for the packaged service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

import json
import shutil

import typer
import uvicorn

from . import schemas
from .config import Settings, get_settings
from .crud import DuplicateUsernameError, create_user, get_user_by_username, list_users
from .database import SessionLocal, init_database
from .publisher import GitHubPublishingError, PublishResult, publish_installers_to_github

app = typer.Typer(help="Manage and run the UCM Color admin backend service.")


def _print_header(title: str) -> None:
    typer.secho(title, bold=True, fg=typer.colors.CYAN)


def _resolve_settings() -> Settings:
    settings = get_settings()
    init_database()
    return settings


@app.command()
def run(
    host: Optional[str] = typer.Option(None, help="Hostname to bind"),
    port: Optional[int] = typer.Option(None, help="Port to expose"),
    reload: Optional[bool] = typer.Option(None, help="Enable auto-reload"),
    log_level: Optional[str] = typer.Option(None, help="Uvicorn log level"),
) -> None:
    """Start the FastAPI service using Uvicorn."""

    settings = _resolve_settings()

    uvicorn.run(
        "ucm_color_admin.app:create_app",
        host=host or settings.host,
        port=port or settings.port,
        reload=settings.reload if reload is None else reload,
        log_level=log_level or settings.log_level,
        factory=True,
    )


@app.command()
def init_db() -> None:
    """Create the SQLite database and tables."""

    settings = _resolve_settings()
    typer.echo(f"Database initialised at {settings.database_path}")
    typer.echo(f"Installer directory ready at {settings.installer_dir}")


@app.command()
def create_admin(
    username: str = typer.Argument(..., help="Unique login name"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Password for the new administrator",
    ),
    email: Optional[str] = typer.Option(None, help="Contact email"),
    full_name: Optional[str] = typer.Option(None, help="Display name"),
    superuser: bool = typer.Option(True, help="Grant superuser privileges"),
) -> None:
    """Create an administrator user in the database."""

    _resolve_settings()
    with SessionLocal() as session:
        if get_user_by_username(session, username):
            typer.secho("User already exists", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        if password is None:
            typer.secho("Password is required", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        try:
            user = create_user(
                session,
                schemas.UserCreate(
                    username=username,
                    password=password,
                    email=email,
                    full_name=full_name,
                    is_superuser=superuser,
                    is_active=True,
                ),
            )
        except DuplicateUsernameError as exc:  # pragma: no cover - handled above
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        typer.secho(f"Created administrator {user.username} (id={user.id})", fg=typer.colors.GREEN)


@app.command("list-users")
def list_users_cmd() -> None:
    """Display users stored in the database."""

    _resolve_settings()
    with SessionLocal() as session:
        users = list_users(session)
        if not users:
            typer.echo("No users found.")
            return
        _print_header("Existing users")
        for user in users:
            typer.echo(
                f"- #{user.id} {user.username} | active={user.is_active} | superuser={user.is_superuser}"
            )


@app.command()
def show_paths() -> None:
    """Print out important filesystem paths."""

    settings = _resolve_settings()
    typer.echo(f"Database: {settings.database_path}")
    typer.echo(f"Config directory: {settings.database_path.parent}")
    typer.echo(f"Installer directory: {settings.installer_dir}")


@app.command("download-installers")
def download_installers(
    source: str = typer.Argument(
        ..., help="Base URL of a running service. Can be the host root or the /downloads endpoint."
    ),
    output: Path = typer.Option(
        Path.cwd(),
        "--output",
        "-o",
        help="Directory where installer archives should be stored.",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Optional specific filename to download. If omitted all installers are retrieved.",
    ),
    overwrite: bool = typer.Option(False, help="Overwrite existing files instead of skipping them."),
) -> None:
    """Download installers exposed by the running API to the local machine."""

    output = output.expanduser()
    output.mkdir(parents=True, exist_ok=True)

    index_url = source.rstrip("/")
    if not index_url.endswith("/downloads"):
        index_url = f"{index_url}/downloads"

    typer.echo(f"Fetching installer index from {index_url}...")
    try:
        with urlopen(index_url) as response:
            payload = response.read().decode("utf-8")
    except URLError as exc:
        typer.secho(f"Failed to connect to {index_url}: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    try:
        raw_entries = json.loads(payload)
    except json.JSONDecodeError as exc:
        typer.secho("Server returned invalid JSON.", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if not isinstance(raw_entries, list):
        typer.secho("Unexpected response format from downloads endpoint.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    entries: list[tuple[str, str]] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        filename = entry.get("filename")
        url = entry.get("url")
        if not filename or not url:
            continue
        if name and filename != name:
            continue
        entries.append((filename, url))

    if name and not entries:
        typer.secho(f"Installer named {name} was not advertised by the server.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not entries:
        typer.secho("No installers available for download.", fg=typer.colors.YELLOW)
        return

    for filename, file_url in entries:
        destination = output / filename
        if destination.exists() and not overwrite:
            typer.secho(
                f"{destination} already exists; skipping. Use --overwrite to replace.",
                fg=typer.colors.YELLOW,
            )
            continue
        typer.echo(f"Downloading {filename}...")
        try:
            with urlopen(file_url) as response, open(destination, "wb") as handle:
                shutil.copyfileobj(response, handle)
        except URLError as exc:
            typer.secho(f"Failed to download {file_url}: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        typer.secho(f"Saved to {destination}", fg=typer.colors.GREEN)


@app.command("publish-installers")
def publish_installers(
    repository: str = typer.Argument(..., help="GitHub repository in the form owner/name."),
    tag: str = typer.Option(..., "--tag", help="Release tag to create or update."),
    name: Optional[str] = typer.Option(None, "--name", help="Release title. Defaults to the tag."),
    notes: Optional[str] = typer.Option(None, "--notes", help="Release notes or description."),
    installer_dir: Optional[Path] = typer.Option(
        None,
        "--installer-dir",
        help="Override the directory containing installer archives. Defaults to the configured installer directory.",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        envvar="GITHUB_TOKEN",
        help="Personal access token with repo scope. Defaults to the GITHUB_TOKEN environment variable.",
    ),
    draft: bool = typer.Option(False, help="Create the release as a draft."),
    prerelease: bool = typer.Option(False, help="Mark the release as a pre-release."),
) -> None:
    """Publish the current installers as GitHub release assets."""

    settings = _resolve_settings()
    source_dir = (installer_dir or settings.installer_dir).expanduser()

    if not source_dir.exists():
        typer.secho(f"Installer directory {source_dir} does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    archives = sorted(
        p for p in source_dir.iterdir() if p.is_file() and p.suffix in {".zip", ".gz", ".whl"}
    )
    if not archives:
        typer.secho(f"No archives found in {source_dir} to publish.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"Publishing {len(archives)} installer(s) from {source_dir} to {repository}@{tag}...")

    try:
        result: PublishResult = publish_installers_to_github(
            repository=repository,
            tag=tag,
            release_name=name,
            notes=notes,
            archives=archives,
            token=token,
            draft=draft,
            prerelease=prerelease,
        )
    except GitHubPublishingError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Release available at {result.release_url}", fg=typer.colors.GREEN)
    for uploaded in result.uploaded_assets:
        typer.echo(f"- {uploaded}")


def main() -> None:
    """Entry-point for console scripts."""

    app()


if __name__ == "__main__":  # pragma: no cover
    main()
