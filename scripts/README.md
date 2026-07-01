# Developer Scripts

This directory contains the root-level PowerShell scripts used to start and manage the local backend server for Queri.ai.

These scripts are tightly coupled to the current repository layout:
```text
backend/
backend/.env
```

If that structure changes, these scripts and this document must be updated together.

## Script Inventory

| Script | Purpose | Hard Dependency |
| :--- | :--- | :--- |
| `backend-server.ps1` | Start FastAPI / Uvicorn dev server | `poetry` on PATH |
| `stop-servers.ps1` | Stop active backend server processes | PowerShell permissions |

---

### `backend-server.ps1`
**Path:** `scripts/backend-server.ps1`

#### Parameters
* `-BindHost` (default: `"0.0.0.0"`)
* `-Port` (default: `8000`)

#### Actual Behavior
1. Resolves repository-relative paths to:
   * `backend/`
   * `backend/.env`
2. Throws immediately if the `backend/` directory or `.env` configuration file is missing.
3. Checks if the `poetry` executable is installed and available in the environment path.
4. Checks the requested port (`$Port`) for active listening TCP processes on the local machine.
5. If the port is occupied, checks both WMI and standard process metrics to identify if it is owned by our uvicorn server (parent or child worker process). If yes, prints an already-running message and exits cleanly (exit code 0) without spawning a second server.
6. If the port is occupied by any other unrelated process, it throws an error and exits to prevent port conflicts.
7. Verifies virtualenv and dependency installation using a dynamic python import check; if missing, it runs `poetry install` to set up dependencies.
8. Displays friendly Title Case local browser access links (e.g. `http://localhost:<Port>` or `http://127.0.0.1:<Port>`) to prevent invalid routes like `0.0.0.0`.
9. Starts the FastAPI server in the current terminal session using:
   ```bash
   poetry run uvicorn app.main:app --host <BindHost> --port <Port> --reload
   ```

#### Important Limits
* It only detects an already-running backend by port ownership plus command-line string matching.
* It does not spawn a detached terminal window.
* It runs the server directly in the active terminal session.

---

### `stop-servers.ps1`
**Path:** `scripts/stop-servers.ps1`

#### Parameters
* `-SkipBackend` (switch)
* `-BackendPorts` (default: `@(8000)`)
* `-GracefulWaitSeconds` (default: `5`)

#### Actual Behavior
1. Supports `-WhatIf` and `-Confirm` flags through `SupportsShouldProcess` for safe dry-runs.
2. Resolves backend path to identify project-scoped processes.
3. Scans active processes for command lines matching uvicorn backend patterns (e.g. `uvicorn` + `app.main:app`).
4. If project-scoped command matching fails to find processes, falls back to port-owner lookup on `-BackendPorts`.
5. Resolves child/orphan worker processes recursively (by matching WMI parent process relations and command-line parent parameters) even when the parent process has already been killed.
6. Gracefully stops processes using `Stop-Process`, waiting up to `$GracefulWaitSeconds` before using forced termination (`Stop-Process -Force`).
7. Uses recursive tree-kill (`-TreeKill`) on matched uvicorn processes to ensure all child worker processes are closed cleanly.
8. Prints step-by-step Title Case logs of all search and termination steps.
9. Prints a Title Case summary showing how many backend processes were found, stopped, or failed.

---

## Practical Usage

### Start Backend Server on Default Port (8000)
```powershell
.\scripts\backend-server.ps1
```

### Start Backend Server on Custom Port and Host
```powershell
.\scripts\backend-server.ps1 -BindHost "127.0.0.1" -Port 8080
```

### Stop Running Backend Server Processes
```powershell
.\scripts\stop-servers.ps1
```

### Stop Backend Server Processes on Custom Ports
```powershell
.\scripts\stop-servers.ps1 -BackendPorts @(8000, 8080)
```

### Dry-Run Shutdown (No Processes Killed)
```powershell
.\scripts\stop-servers.ps1 -WhatIf
```
