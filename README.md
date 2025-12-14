# J-Dep Analyzer (Web)

A web app to upload Maven `pom.xml` files, parse direct dependencies, store them in SQLite, and explore them via an interactive graph and list views.

## Requirements

- Python >= 3.10
- `uv` installed

## Install

```bash
uv sync --extra dev
```

## Run

```bash
uv run fastapi dev src/main.py
```

Then open:

- <http://127.0.0.1:8000/>

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
