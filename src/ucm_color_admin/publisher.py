"""Utilities for publishing installer archives to GitHub releases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
UPLOAD_ROOT = "https://uploads.github.com"
USER_AGENT = "ucm-color-admin-installer"


class GitHubPublishingError(RuntimeError):
    """Raised when communication with the GitHub API fails."""


@dataclass(slots=True)
class PublishResult:
    """Outcome of a release publishing attempt."""

    release_url: str
    uploaded_assets: list[str]


def _build_headers(token: Optional[str], content_type: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"token {token}"
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _request(
    method: str,
    url: str,
    token: Optional[str],
    *,
    payload: Optional[dict[str, object]] = None,
    data: Optional[bytes] = None,
    content_type: Optional[str] = None,
    accepted_errors: tuple[int, ...] = (),
) -> tuple[int, bytes]:
    """Execute an HTTP request against the GitHub API and return the response."""

    if payload is not None and data is not None:
        raise ValueError("Provide either payload or data, not both.")

    body: Optional[bytes] = data
    headers = _build_headers(token, content_type)

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(request) as response:
            return response.status, response.read()
    except HTTPError as exc:  # pragma: no cover - network error handling
        if exc.code in accepted_errors:
            return exc.code, exc.read()
        message = exc.read().decode("utf-8", errors="replace")
        raise GitHubPublishingError(f"{method} {url} failed with {exc.code}: {message}") from exc


def _load_json(data: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected API response
        raise GitHubPublishingError("GitHub API returned invalid JSON") from exc
    if not isinstance(decoded, dict):  # pragma: no cover - unexpected API response
        raise GitHubPublishingError("Unexpected JSON structure returned by GitHub")
    return decoded


def _get_release_by_tag(repository: str, tag: str, token: Optional[str]) -> dict[str, object]:
    status, body = _request("GET", f"{API_ROOT}/repos/{repository}/releases/tags/{tag}", token)
    if status != 200:  # pragma: no cover - handled by _request
        raise GitHubPublishingError(f"Unable to fetch release for tag {tag}")
    return _load_json(body)


def _create_or_get_release(
    repository: str,
    tag: str,
    *,
    release_name: Optional[str],
    notes: Optional[str],
    token: Optional[str],
    draft: bool,
    prerelease: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "tag_name": tag,
        "name": release_name or tag,
        "body": notes or "",
        "draft": draft,
        "prerelease": prerelease,
    }
    status, body = _request(
        "POST",
        f"{API_ROOT}/repos/{repository}/releases",
        token,
        payload=payload,
        accepted_errors=(422,),
    )
    if status == 201:
        return _load_json(body)
    # 422 indicates a release already exists; fetch it instead
    release = _get_release_by_tag(repository, tag, token)
    # Keep metadata in sync when notes/title change
    release_id = release.get("id")
    if isinstance(release_id, int):
        _request(
            "PATCH",
            f"{API_ROOT}/repos/{repository}/releases/{release_id}",
            token,
            payload={"name": release_name or tag, "body": notes or "", "draft": draft, "prerelease": prerelease},
        )
        release = _get_release_by_tag(repository, tag, token)
    return release


def _delete_existing_asset(repository: str, asset_id: int, token: Optional[str]) -> None:
    _request(
        "DELETE",
        f"{API_ROOT}/repos/{repository}/releases/assets/{asset_id}",
        token,
        accepted_errors=(204, 404),
    )


def _upload_asset(repository: str, release_id: int, archive: Path, token: Optional[str]) -> None:
    with archive.open("rb") as handle:
        data = handle.read()
    query = urlencode({"name": archive.name})
    url = f"{UPLOAD_ROOT}/repos/{repository}/releases/{release_id}/assets?{query}"
    _request(
        "POST",
        url,
        token,
        data=data,
        content_type="application/octet-stream",
    )


def publish_installers_to_github(
    *,
    repository: str,
    tag: str,
    release_name: Optional[str],
    notes: Optional[str],
    archives: Iterable[Path],
    token: Optional[str],
    draft: bool = False,
    prerelease: bool = False,
) -> PublishResult:
    """Upload the given archives to a GitHub release, creating it if necessary."""

    archives = list(archives)
    if not archives:
        raise GitHubPublishingError("No archives supplied for publishing.")

    release = _create_or_get_release(
        repository,
        tag,
        release_name=release_name,
        notes=notes,
        token=token,
        draft=draft,
        prerelease=prerelease,
    )

    release_id = release.get("id")
    upload_url = release.get("upload_url")
    html_url = release.get("html_url")
    assets = release.get("assets", [])

    if not isinstance(release_id, int) or not isinstance(upload_url, str) or not isinstance(html_url, str):
        raise GitHubPublishingError("GitHub response did not contain release identifiers.")

    existing_assets: dict[str, int] = {}
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict):
                name = asset.get("name")
                asset_id = asset.get("id")
                if isinstance(name, str) and isinstance(asset_id, int):
                    existing_assets[name] = asset_id

    uploaded: list[str] = []

    for archive in archives:
        if not archive.is_file():
            raise GitHubPublishingError(f"Archive {archive} does not exist or is not a file.")
        asset_id = existing_assets.get(archive.name)
        if asset_id is not None:
            _delete_existing_asset(repository, asset_id, token)
        _upload_asset(repository, release_id, archive, token)
        uploaded.append(archive.name)

    # Refresh release data to ensure we return the latest URL
    release = _get_release_by_tag(repository, tag, token)
    html_url = release.get("html_url", html_url)

    if not isinstance(html_url, str):  # pragma: no cover - defensive fallback
        raise GitHubPublishingError("GitHub response did not provide a release URL.")

    return PublishResult(release_url=html_url, uploaded_assets=uploaded)


__all__ = [
    "GitHubPublishingError",
    "PublishResult",
    "publish_installers_to_github",
]
