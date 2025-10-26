# UCM Color Admin Installer

This project packages the UCM Color backend management service as a
cross-platform installer so that operators can download, install, and
run the API without needing to manually provision dependencies.

## Features

- FastAPI based backend with SQLite persistence.
- Typer powered CLI for administration tasks such as creating an admin
  user or inspecting paths, automating downloads, and pushing releases.
- Packaging via Python wheels with helper installers for Linux/macOS
  (`install.sh`) and Windows (`install.ps1`).
- Automated `scripts/build_installer.sh` script that produces ready to
  share archives.
- Built-in `/downloads` API that lists installers and serves them
  directly to end users.

## Project layout

```
├── installer/              # Installer templates bundled with releases
├── scripts/                # Helper scripts
├── src/ucm_color_admin/    # Application source code
└── pyproject.toml          # Packaging configuration
```

## Development setup

Create a virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

Launch the API locally:

```
ucm-color-admin run --reload
```

Access the interactive API docs at <http://127.0.0.1:8000/docs>.

## Database management

The service stores data in a SQLite database located at
`~/.ucm_color_admin/database.sqlite3` by default. Use the CLI to manage
initial state:

```
ucm-color-admin init-db
ucm-color-admin create-admin admin --password supersecret --email admin@example.com
ucm-color-admin list-users
```

## Building installer artifacts

Run the helper script to build wheels and wrap them into OS-specific
archives:

```
bash scripts/build_installer.sh
```

The resulting files are placed under `dist/installers/`. Each archive
contains the wheel and platform-specific installer script. End users
can unpack the archive and run the installer script directly.

## Exporting a full project archive

To share the entire repository tree—for example when transferring it to
another machine—compress the workspace directory into a zip file and
copy it to a shareable location:

```bash
cd /workspace
zip -r UCM-Color.zip UCM-Color
cp UCM-Color.zip /mnt/data/UCM-Color.zip
```

The `/mnt/data` directory is exposed to the host environment in Codex
workspaces, so any files placed there can be downloaded via the
interface.

## Publishing direct download links

1. Copy the generated archives from `dist/installers/` into the
   directory reported by `ucm-color-admin show-paths` (defaults to
   `~/.ucm_color_admin/installers`).
2. Start the service (for example with `ucm-color-admin run`).
3. Visit `http://<host>:<port>/downloads` to obtain a JSON list of
   available installers along with direct URLs.
4. Share the URL `http://<host>:<port>/downloads/<filename>` with end
   users so they can download the installer in a browser or via `curl`
   and `wget`.

### Automated downloads for local testing

Codex or other automation agents can fetch the latest installers using
the CLI without manual interaction:

```
ucm-color-admin download-installers http://127.0.0.1:8000 --output ./downloaded
```

The command connects to the `/downloads` endpoint, retrieves metadata,
and downloads the exposed archives into the requested directory. Use
`--name` to fetch a specific installer and `--overwrite` to replace
existing files when re-running after a rebuild.

### Publishing installers to GitHub releases

After rebuilding installers, publish them to GitHub with a single
command. Provide a personal access token in the `GITHUB_TOKEN`
environment variable or through the `--token` option.

```
export GITHUB_TOKEN=ghp_example123
ucm-color-admin publish-installers example/ucm-color --tag v0.2.0 --notes "Automated download helpers"
```

The command creates (or updates) the release, uploads the
`*.tar.gz`/`*.zip` archives from the configured installer directory, and
prints the resulting release URL—ideal for Codex driven workflows that
need to push fresh builds to GitHub automatically.

### Linux/macOS installation

```
tar -xzf ucm-color-admin-0.1.0-linux-macos.tar.gz
cd ucm-color-admin-0.1.0
chmod +x install.sh
./install.sh /opt/ucm-color-admin
```

The installer creates an isolated virtual environment and a launcher
script `ucm-color-admin.sh` inside the installation directory.

### Windows installation

```
Expand-Archive ucm-color-admin-0.1.0-windows.zip
cd ucm-color-admin-0.1.0
powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "C:\\UCMColorAdmin"
```

After installation run:

```
powershell -File C:\\UCMColorAdmin\\ucm-color-admin.ps1 run
```

## Configuration

Environment variables allow overriding defaults when running the
service or CLI:

- `UCM_COLOR_HOST` – host to bind (default `127.0.0.1`).
- `UCM_COLOR_PORT` – port to use (default `8000`).
- `UCM_COLOR_RELOAD` – set to `true` to enable auto reload.
- `UCM_COLOR_DB` – absolute path to the SQLite database file.
- `UCM_COLOR_INSTALLER_DIR` – directory that the `/downloads`
  endpoints expose (default `~/.ucm_color_admin/installers`).

## License

This project is released under the MIT License. See [LICENSE](LICENSE)
for details.
