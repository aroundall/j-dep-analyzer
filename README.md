# J-Dep Analyzer (Web)

A web app to upload Maven `pom.xml` files, parse direct dependencies, store them in SQLite, and explore them via an interactive graph and list views.

## Requirements

- Python >= 3.10
- Either `uv` (recommended) or `pip`

Notes:

- Python 3.11/3.12 is recommended for best wheel availability on all platforms.
- Windows users: this repo uses a `src/` layout, so when starting with `uvicorn` you typically need `--app-dir src` (see below).

## Install (uv)

```bash
uv sync --extra dev
```

## Run (uv)

```bash
uv run fastapi dev src/main.py
```

Then open:

- <http://127.0.0.1:8000/>

## Install (pip)

This repo is a Python package (with a `src/` layout), so the simplest `pip` flow is to install it into a virtualenv.

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Windows (CMD):

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
pip install -e ".[dev]"
```

## Run (pip)

Because of the `src/` layout, prefer `--app-dir src` so `j_dep_analyzer` imports correctly.

Linux/macOS:

```bash
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Windows (PowerShell):

```powershell
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Windows (CMD):

```bat
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

If you prefer keeping the original module path (`uvicorn src.main:app ...`), you must add `src/` to `PYTHONPATH`:

- PowerShell: `$env:PYTHONPATH = "src"`
- CMD: `set PYTHONPATH=src`

## Using the App

### 1) Upload POM files

- Go to `/` (Dashboard)
- Use the upload form to upload one or more `pom.xml` (or `*.pom`) files
- The server parses each file and inserts:
  - Artifacts (GAV)
  - Dependency edges (A -> B means "A depends on B")

Notes:

- If a dependency version cannot be resolved (e.g. `${...}` not found), it is stored as `Unknown` (tolerant parsing).

### 2) Explore the global graph

On `/` you can toggle:

- **Show Group**: when off, nodes are merged by `artifactId` (and optionally version)
- **Show Version**: when off, nodes are merged across versions
- **Direction**:
  - `forward`: A depends on B (A -> B)
  - `reverse`: who depends on B (still A -> B, but highlights predecessors of the selected root)
- **Depth**: limit graph to N hops (or All)
- **Layout**: `dagre` or `cose`

### 3) Browse artifacts

- Go to `/list`
- Filter by `artifactId`
- Click any row to open details view for that artifact

### 4) Dependencies pair list

- Go to `/dependencies/list`
- Filter by `artifactId` (matches source or target)
- Use checkboxes:
  - **Ignore Version**: deduplicate pairs across versions
  - **Ignore GroupId**: deduplicate pairs across groupId
- Click a row to open the target details view

### 5) Details view

- `/details/{gav}` (alias of `/visualize/{gav}`)
- Shows a graph centered at the selected root
- Supports direction, depth, and aggregation toggles

## Data Storage

By default the app uses a SQLite database file in the repo root:

- `dependencies.db`

To change it:

```bash
export JDEP_DB_PATH=/path/to/your/dependencies.db
uv run fastapi dev src/main.py
```

Windows (PowerShell):

```powershell
$env:JDEP_DB_PATH = "C:\\path\\to\\dependencies.db"
uv run fastapi dev src/main.py
```

Windows (CMD):

```bat
set JDEP_DB_PATH=C:\path\to\dependencies.db
uv run fastapi dev src/main.py
```

## API Endpoints

- `POST /api/upload` – upload POM files (multipart form field: `files`)
- `GET /api/artifacts` – list artifacts
- `GET /api/graph/data` – Cytoscape.js elements JSON
  - Query params: `root_id` (optional), `direction` (`forward|reverse`), `depth` (optional), `show_group` (bool), `show_version` (bool)

## Development

Run tests:

```bash
uv run pytest
```
