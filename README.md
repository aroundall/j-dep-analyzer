# J-Dep Analyzer (Web)

A web app to upload Maven `pom.xml` files, parse direct dependencies, store them in a database (SQLite or GCP CloudSQL PostgreSQL), and explore them via an interactive graph and list views.

## Requirements

- Python >= 3.10
- Either `uv` (recommended) or `pip`

> **Note**: Python 3.11/3.12 is recommended for best wheel availability.

---

## Quick Start

### Linux / macOS

<details>
<summary><strong>Using uv (recommended)</strong></summary>

```bash
# Install
uv sync --extra dev

# Run (SQLite - default)
uv run fastapi dev src/main.py

# Run (CloudSQL PostgreSQL)
export JDEP_DB_TYPE=postgresql
export JDEP_DB_HOST=your-project:region:instance
export JDEP_DB_NAME=jdep
export JDEP_DB_USER=your-user
export JDEP_DB_PASSWORD=your-password
export JDEP_GCP_CREDENTIALS=/path/to/service-account.json
uv run alembic upgrade head
uv run fastapi dev src/main.py
```

</details>

<details>
<summary><strong>Using pip</strong></summary>

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

# Run (SQLite - default)
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000

# Run (CloudSQL PostgreSQL)
export JDEP_DB_TYPE=postgresql
export JDEP_DB_HOST=your-project:region:instance
export JDEP_DB_NAME=jdep
export JDEP_DB_USER=your-user
export JDEP_DB_PASSWORD=your-password
export JDEP_GCP_CREDENTIALS=/path/to/service-account.json
alembic upgrade head
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

</details>

---

### Windows

<details>
<summary><strong>Using uv (recommended) - PowerShell</strong></summary>

```powershell
# Install
uv sync --extra dev

# Run (SQLite - default)
uv run fastapi dev src/main.py

# Run (CloudSQL PostgreSQL)
$env:JDEP_DB_TYPE = "postgresql"
$env:JDEP_DB_HOST = "your-project:region:instance"
$env:JDEP_DB_NAME = "jdep"
$env:JDEP_DB_USER = "your-user"
$env:JDEP_DB_PASSWORD = "your-password"
$env:JDEP_GCP_CREDENTIALS = "C:\path\to\service-account.json"
uv run alembic upgrade head
uv run fastapi dev src/main.py
```

</details>

<details>
<summary><strong>Using pip - PowerShell</strong></summary>

```powershell
# Install
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"

# Run (SQLite - default)
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000

# Run (CloudSQL PostgreSQL)
$env:JDEP_DB_TYPE = "postgresql"
$env:JDEP_DB_HOST = "your-project:region:instance"
$env:JDEP_DB_NAME = "jdep"
$env:JDEP_DB_USER = "your-user"
$env:JDEP_DB_PASSWORD = "your-password"
$env:JDEP_GCP_CREDENTIALS = "C:\path\to\service-account.json"
alembic upgrade head
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

</details>

<details>
<summary><strong>Using pip - CMD</strong></summary>

```bat
:: Install
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
pip install -e ".[dev]"

:: Run (SQLite - default)
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000

:: Run (CloudSQL PostgreSQL)
set JDEP_DB_TYPE=postgresql
set JDEP_DB_HOST=your-project:region:instance
set JDEP_DB_NAME=jdep
set JDEP_DB_USER=your-user
set JDEP_DB_PASSWORD=your-password
set JDEP_GCP_CREDENTIALS=C:\path\to\service-account.json
alembic upgrade head
uvicorn main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

</details>

---

Then open: <http://127.0.0.1:8000/>

---

## Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `JDEP_DB_TYPE` | `sqlite` or `postgresql` | `sqlite` |
| `JDEP_DB_PATH` | SQLite database file path | `dependencies.db` |
| `JDEP_DB_HOST` | CloudSQL instance (`project:region:instance`) | - |
| `JDEP_DB_NAME` | Database name | `jdep` |
| `JDEP_DB_USER` | Database user | - |
| `JDEP_DB_PASSWORD` | Database password | - |
| `JDEP_GCP_CREDENTIALS` | Path to GCP service account JSON | - |

See `.env.example` for a complete template.

---

## Database Migrations (Alembic)

```bash
uv run alembic current              # View status
uv run alembic upgrade head         # Apply migrations
uv run alembic downgrade -1         # Rollback one
uv run alembic revision --autogenerate -m "desc"  # Generate new
```

---

## Using the App

### 1) Upload POM files

- Go to `/` (Dashboard)
- Upload one or more `pom.xml` files
- Server parses and stores artifacts + dependency edges

### 2) Explore the global graph

Toggle options: **Show Group**, **Show Version**, **Direction**, **Depth**, **Layout**

### 3) Dependencies pair list

- Go to `/dependencies/list`
- Filter by `artifactId`, use **Ignore Version** / **Ignore GroupId** checkboxes

### 4) Details view

- `/details/{gav}` - Graph centered on selected artifact

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/upload` | Upload POM files (multipart: `files`) |
| `GET /api/artifacts` | List artifacts |
| `GET /api/graph/data` | Cytoscape.js graph data |

---

## Development

```bash
uv run pytest  # Run tests
```
