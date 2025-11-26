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
- Integrated `/web/login` portal that provides browser-based login and
  user management forms without needing an external front-end.

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

> **Windows note:** On Windows 10, create the virtual environment with
> `py -3 -m venv .venv` and activate it via
> `.venv\Scripts\Activate.ps1`.

## Web 登录与表单中心

Create your first administrator with the CLI and then manage users in a
browser without writing additional code:

1. Run `ucm-color-admin create-admin <username> --password <pwd>`.
2. Start the API via `ucm-color-admin run` (or the installed service).
3. Open <http://127.0.0.1:8000/web/login> to access the login portal.
4. 登录后自动跳转到 `/web/dashboard` 主控台：左侧树状菜单列出业务模块，右侧显示检查页头和检查列表，便于核对上线范围。
5. 使用右上角的“用户表单”按钮进入 `/web/forms`，这里提供创建、更新、删除用户的 HTML 表单。

主控台涵盖的业务检查模块：

- 商品（Catalog）：条码、价格、批量导入导出、富媒体与查询编辑。
- 库存（Inventory）：库存流水、盘点调整、低库存/滞销预警、ATS 与门店调拨。
- 会员（CRM）：会员档案、积分规则、隐私合规导出、等级与优惠、清费记录。
- 订单（OMS/Orders）：多维筛选、状态流转、退款/作废、渠道对账导出。
- 营销与分析（Marketing & BI）：满减/折扣/券、看板报表、门店/区域多维透视。
- 系统（System）：用户/角色/权限、API 密钥、审计日志与定时任务。

The session is stored in an HTTP-only cookie for eight hours. Use the
“退出” button in the UI (or visit `/web/logout`) to clear it. These
pages share the same SQLite database as the API, so actions performed in
the browser are immediately reflected in API responses and vice versa.

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

On Windows PowerShell (including Windows 10 Home), use the dedicated
script instead:

```
powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
```

Pass `-PythonCommand py` or `-PythonCommand python` if a specific
interpreter should be used.

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
ucm-color-admin publish-installers example/ucm-color --tag v0.3.0 --notes "Web login portal"
```

The command creates (or updates) the release, uploads the
`*.tar.gz`/`*.zip` archives from the configured installer directory, and
prints the resulting release URL—ideal for Codex driven workflows that
need to push fresh builds to GitHub automatically.

### Linux/macOS installation

```
tar -xzf ucm-color-admin-0.3.0-linux-macos.tar.gz
cd ucm-color-admin-0.3.0
chmod +x install.sh
./install.sh /opt/ucm-color-admin
```

The installer creates an isolated virtual environment and a launcher
script `ucm-color-admin.sh` inside the installation directory.

### Windows installation

```
Expand-Archive ucm-color-admin-0.3.0-windows.zip
cd ucm-color-admin-0.3.0
powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "C:\\UCMColorAdmin"
```

After installation run:

```
powershell -File C:\\UCMColorAdmin\\ucm-color-admin.ps1 run
```

The default data location on Windows is
`%LOCALAPPDATA%\UCMColorAdmin`, matching the installer defaults.

## Configuration

Environment variables allow overriding defaults when running the
service or CLI:

- `UCM_COLOR_HOST` – host to bind (default `127.0.0.1`).
- `UCM_COLOR_PORT` – port to use (default `8000`).
- `UCM_COLOR_RELOAD` – set to `true` to enable auto reload.
- `UCM_COLOR_DB` – absolute path to the SQLite database file. Defaults
  to `%LOCALAPPDATA%\UCMColorAdmin\database.sqlite3` on Windows and
  `~/.ucm_color_admin/database.sqlite3` elsewhere.
- `UCM_COLOR_INSTALLER_DIR` – directory that the `/downloads`
  endpoints expose (default `%LOCALAPPDATA%\UCMColorAdmin\installers`
  on Windows and `~/.ucm_color_admin/installers` on Linux/macOS).

## Windows 10 Home + Docker Desktop testing workflow

Windows 10 Home users with Docker Desktop 4.46.0 can run the backend in
an isolated container for local verification:

1. Ensure WSL 2 integration is enabled in Docker Desktop.
2. From PowerShell, build the image (requires internet access to fetch
   Python packages):

   ```powershell
   docker build -t ucm-color-admin:latest .
   ```

3. Launch the container, binding the API port and mounting a host
   directory so installers and the SQLite database persist between
   runs:

   ```powershell
   docker run --rm -p 8000:8000 `
     -v "$Env:LOCALAPPDATA\UCMColorAdmin:/data" `
     -e UCM_COLOR_DB=/data/database.sqlite3 `
     -e UCM_COLOR_INSTALLER_DIR=/data/installers `
     ucm-color-admin:latest
   ```

4. Once the container reports that Uvicorn started, open
   <http://127.0.0.1:8000/docs> in the browser to interact with the API
   or invoke CLI commands via:

   ```powershell
   docker exec -it <container-id> ucm-color-admin list-users
   ```

This workflow mirrors the packaged defaults, ensuring that archives
downloaded from `/downloads` behave the same way as an on-host
installation.

## Exporting the entire project as a ZIP archive

When you need to share the full repository contents—for example to attach
them to a support ticket or provide Codex with a reproducible snapshot—run
the bundled export helper. The script skips transient directories such as
`.git`, build artefacts, and caches so the resulting archive stays lean.

```bash
python scripts/export_project.py --output dist/UCM-Color.zip
```

The command writes the archive to `dist/UCM-Color.zip` by default. You can
specify a custom path with `--output` or include the Git metadata with
`--include-git` if you need the commit history.

To make the archive available for download in this coding environment,
copy it into `/mnt/data` after exporting:

```bash
cp dist/UCM-Color.zip /mnt/data/UCM-Color.zip
```

The `/mnt/data` directory is exposed via the “Download file” UI so you can
transfer the archive to your Windows workstation for local testing.

## License

This project is released under the MIT License. See [LICENSE](LICENSE)
for details.
