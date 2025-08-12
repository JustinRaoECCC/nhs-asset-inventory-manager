# NHS Asset Inventory Manager

Upload two Excel workbooks, normalize them into a clean JSON schema, explore them as a collapsible tree, and compare **asset presence** across sources. Run it as a desktop app (pywebview) or as a local FastAPI service in development.

> Built for station‑centric **Asset Inventory (FINAL …)** and asset‑centric **HYDEX** spreadsheets.

---

## Table of Contents

- [Key Features](#key-features)
- [Screens & Workflow](#screens--workflow)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running](#running)
  - [Desktop App (recommended)](#desktop-app-recommended)
  - [Dev Server (for development)](#dev-server-for-development)
- [Usage](#usage)
- [Data Model](#data-model)
  - [Normalized JSON Schema](#normalized-json-schema)
  - [Comparison Output](#comparison-output)
- [API Reference](#api-reference)
- [Implementation Details](#implementation-details)
- [Troubleshooting](#troubleshooting)
- [Security & Privacy](#security--privacy)
- [Extending the App](#extending-the-app)
- [Requirements](#requirements)
- [License](#license)

---

## Key Features

- **Desktop app** experience (no browser) via **pywebview** (`python desktop/app.py`).
- **In-memory uploads**: your Excel files are **not** stored on disk; they exist only for the current session.
- **One-click comparison**: “**Compare Missing Infrastructure →**” highlights per‑station differences between sources.
- **HYDEX-only stations**: build a table of stations present in HYDEX but missing from Asset Inventory; export to **.xlsx**.
  - In the desktop app, export uses a **native Save As…** dialog to save the file exactly where you choose.
  - In a browser, the export streams as a normal file download.
- **Two bottom tabs**: “Comparison Results” (diff cards) and “HYDEX‑only Stations” (table with export).
- **Thoughtful normalization**:
  - Station‑centric (Asset Inventory): treats only **boolean‑ish** columns whose headers look like assets (e.g., *Cableway, Weir, Well, Metering Bridge, Shelter, Helicopter Pad, Flume*) as assets.  
    Non‑asset columns (e.g., “Condition”, “Status”, “Type”, “In Service”, “ID”, etc.) remain **attributes**.
  - Asset‑centric (HYDEX): parses rows as **category / value / status / date / note**. Maps categories like **“SHELTER TYPE” → Shelter**, **“WELL TYPE” → Well** to assets; ignores non‑asset categories (e.g., “Installation Type”). Counts assets only if **status is active** (not mothballed / removed / inactive).
  - **Station attributes from HYDEX** (lat/lon, province, office, technician) are aggregated per station.
- **Data hygiene**:
  - **Ignore** Asset Inventory “**Start Time**” and “**Completion Time**” attributes.
  - All date‑like values coerced to **`YYYY‑MM‑DD`** (date only).
  - Asset Inventory tree shows **only Station ID** in the header; technician name is included under **Attributes**.
- **Session correctness**: comparison runs only if **both** files were uploaded **in this session**; stale JSON on disk is ignored.
- **JSON snapshots (overwritten)** for easy inspection: `data/json/asset_inventory.json`, `data/json/hydex.json` (replaced on each upload).

---

## Screens & Workflow

1. **Left panel**: Upload **Asset Inventory (station‑centric)** Excel.
2. **Right panel**: Upload **HYDEX (asset‑centric)** Excel.
3. Inspect each dataset via a collapsible **tree**:
   - Station header:  
     - Asset Inventory → **Station ID only**  
     - HYDEX → **Station Name • Station ID**
   - **Attributes** (station‑level metadata)
   - **Assets** (canonical list; each asset expands to show attributes)
4. Center buttons:
   - **Compare Missing Infrastructure →** shows per‑station differences (missing assets between sources).
   - **Find HYDEX‑only Stations** builds a table of stations present in HYDEX but not in Asset Inventory; export to Excel.
5. Bottom tabs:
   - **Comparison Results** → discrepancy cards.
   - **HYDEX‑only Stations** → table with columns **Station ID | Station Name | Province | Office | Tech Name** and **Export to Excel (.xlsx)**.

---

## Architecture

- **Frontend**: vanilla JS + HTML + CSS served by FastAPI. Implements uploads, trees, tabs, comparison view, and exporting.
- **Backend**: FastAPI app with endpoints for upload/normalize/compare/export.
- **Desktop shell**: `pywebview` window that runs the FastAPI server in a background thread and hosts the UI in a native window. Provides a **Save As…** function via a JS bridge for exports.

---

## Project Structure

```
nhs-asset-inventory-manager/
├─ backend/
│  ├─ __init__.py
│  ├─ app.py                    # FastAPI entrypoint and endpoints
│  ├─ models.py                 # Pydantic models (Inventory, Station, Asset)
│  ├─ parsers/
│  │  ├─ __init__.py
│  │  ├─ station_centric.py     # Asset Inventory parser
│  │  ├─ asset_centric.py       # HYDEX parser
│  │  └─ utils.py               # Heuristics & helpers
│  └─ services/
│     ├─ comparator.py          # Asset presence diff
│     ├─ normalizer.py          # Excel → DataFrame → Inventory
│     ├─ storage.py             # JSON IO (date-only serialization)
│     └─ report.py              # HYDEX-only stations & Excel export
├─ desktop/
│  └─ app.py                    # Desktop launcher (pywebview + Save As…)
├─ frontend/
│  ├─ index.html
│  ├─ app.js                    # UI logic, tabs, trees, export
│  └─ styles.css
├─ data/
│  └─ json/                     # Overwritten normalized JSON snapshots
├─ .gitignore
├─ requirements.txt
└─ README.md
```

---

## Installation

```bash
# 1) Clone and enter the repo
git clone https://github.com/JustinRaoECCC/nhs-asset-inventory-manager.git
cd nhs-asset-inventory-manager

# 2) Create & activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scriptsctivate
# macOS/Linux:
source .venv/bin/activate

# 3) Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> If you previously created the repo locally and only need to set the remote:  
> `git remote add origin https://github.com/JustinRaoECCC/nhs-asset-inventory-manager.git`

---

## Running

### Desktop App (recommended)

```bash
python desktop/app.py
```

- A native window opens (“**NHS Asset Inventory Manager**”).  
- Upload the two Excel files for **this session** (files are **not** saved to disk).  
- Click **Compare Missing Infrastructure →** to see per‑station differences.  
- Click **Find HYDEX‑only Stations** to build the table and **Export to Excel**.  
- In desktop mode, export uses a native **Save As…** dialog (choose destination and filename).

### Dev Server (for development)

```bash
uvicorn backend.app:app --reload
# open http://127.0.0.1:8000
```

---

## Usage

1. **Upload Asset Inventory (station‑centric)** on the left.
2. **Upload HYDEX (asset‑centric)** on the right.
3. Inspect each dataset in the tree.
4. **Compare Missing Infrastructure →**
   - Left = Asset Inventory; Right = HYDEX.
   - “Missing in …” shows which assets exist in one source but not the other.
5. **Find HYDEX‑only Stations**
   - Produces a table with columns: **Station ID | Station Name | Province | Office | Tech Name**.
   - Use **Export to Excel (.xlsx)** to download/save the list.

---

## Data Model

### Normalized JSON Schema

```jsonc
{
  "source": "asset_inventory | hydex",
  "generated_at": "2025-08-12T12:00:00Z",
  "stations": [
    {
      "station_id": "08NA005",
      "station_name": "Some Station",        // HYDEX may include this; Asset Inventory shows ID in UI
      "attributes": {                         // Station-level metadata
        "Province": "NB",
        "Office": "FREDERICTON",
        "Tech Name": "MELISSA CONDIE",
        "Latitude": 47.20658,
        "Longitude": -68.95555
      },
      "assets": [
        { "type": "Cableway", "attributes": {} },
        { "type": "Weir",     "attributes": { "value": "V-notched", "status": "ACTIVE", "date": "2002-07-09" } }
      ]
    }
  ]
}
```

### Comparison Output

```json
{
  "summary": {
    "stations_compared": 123,
    "stations_with_discrepancies": 7
  },
  "details": [
    {
      "station_id": "01AD003",
      "station_name_left": "St. Francis River at Outlet of Glasier Lake",
      "station_name_right": "St. Francis River at Outlet of Glasier Lake",
      "source_left": "asset_inventory",
      "source_right": "hydex",
      "assets_left": ["Cableway"],
      "assets_right": ["Shelter"],
      "missing_in_left": ["Shelter"],
      "missing_in_right": ["Cableway"]
    }
  ]
}
```

---

## API Reference

- `GET /` → Frontend (single page UI)
- `POST /api/upload/asset_inventory`  
  Upload station‑centric Excel; normalizes and **overwrites** `data/json/asset_inventory.json`.  
  Returns the normalized `Inventory` payload.
- `POST /api/upload/hydex`  
  Upload HYDEX Excel; normalizes and **overwrites** `data/json/hydex.json`.  
  Returns the normalized `Inventory` payload.
- `GET /api/json/{name}` → Fetch saved JSON (`asset_inventory` | `hydex`) for inspection.
- `GET /api/compare` → Compare current session inventories (asset presence diff).  
  **Requires both** files uploaded in this session.
- `GET /api/missing_stations` → JSON rows of HYDEX‑only stations.
- `GET /api/export/missing_stations.xlsx` → Streams HYDEX‑only table as `.xlsx` (browser flow).  
  In desktop mode, **Save As…** is handled via `window.pywebview.api` (no server-side save).

---

## Implementation Details

- **Station‑centric (Asset Inventory) parsing**
  - Detect **Station ID** and (optional) **Station Name** columns heuristically.
  - A column becomes an **asset flag** only if:
    1) The **header** matches known asset patterns (Cableway, Weir, Well, Metering Bridge, Shelter, Helicopter Pad, Flume), **and**
    2) The **values** are boolean‑ish (Yes/No, X/blank, 0/1, True/False).
  - Everything else becomes **attributes** (except “Start Time” / “Completion Time”, which are ignored).
  - UI header shows **Station ID only**; technician name surfaces under **Attributes**.

- **Asset‑centric (HYDEX) parsing**
  - Interprets each row as **category / value / status / date / note**.
  - Maps categories → assets (e.g., “SHELTER TYPE” → `Shelter`, “WELL TYPE” → `Well`).  
    **Ignores** categories like “Installation Type”.
  - Only counts assets with **active** status (not mothballed / removed / inactive).
  - Aggregates station attributes by grouping rows per **Station ID**:
    - For **lat/lon**: numeric mean rounded to 6 decimals.
    - For other fields (province, office, tech): single consistent value, or dominant mode if clearly prevailing.

- **Dates**
  - All date‑like values serialized as **`YYYY‑MM‑DD`** (date only).
  - Enforced both in parsers and JSON serialization.

- **Session model**
  - Server keeps in‑memory `CURRENT["asset_inventory"]` and `CURRENT["hydex"]`.
  - `/api/compare`, `/api/missing_stations`, and export endpoints **require both** to be present in the same run.
  - Normalized JSON in `data/json/*.json` is **overwritten** on each upload; old state is cleared on startup.

- **No uploaded Excel persistence**
  - Upload handlers read files into memory (`bytes`) and do **not** write them to disk.

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'backend'` when launching desktop**  
  Ensure `backend/__init__.py` exists and `desktop/app.py` adds the project root to `sys.path` (included). Run from repo root:
  ```bash
  python desktop/app.py
  ```

- **Port 8000 already in use**  
  Stop other processes using 8000 or change the port in `desktop/app.py` and the window URL.

- **Export not saving to the chosen path (desktop)**  
  Confirm you’re running the desktop app. In desktop mode, export uses a native **Save As…** dialog. In a browser, it downloads to the default Downloads folder.

- **Unexpected assets (e.g., “Condition” appears as an asset)**  
  The parser filters these. If headers are unusual, add patterns in `backend/parsers/utils.py` (`ASSET_PATTERNS`, `EXCLUDE_IN_HEADER`, `category_to_asset`).

- **Dates include time**  
  Restart the app after updating. Parsers and serializer coerce to date‑only.

---

## Security & Privacy

- Excel uploads are processed **in memory** and **not** saved to disk.
- Normalized JSON snapshots are overwritten on each upload.
- No authentication is implemented (single‑user desktop scenario). Add auth if deploying multi‑user or networked.

---

## Extending the App

- Add CSV support (alongside Excel) in `services/normalizer.py`.
- Mapping UI to manually select Station ID / Name / Asset Type columns for edge‑case files.
- Export comparison results to CSV/Excel.
- Bundle as a **single EXE** (via PyInstaller) for Windows distribution.

---

## Requirements

```
fastapi
uvicorn[standard]
pandas
openpyxl
python-multipart
pydantic
pywebview
```

---

## License

Choose a license for your repository (e.g., MIT, Apache‑2.0) and add a `LICENSE` file. If you’re unsure, MIT is a common default for internal tools.
