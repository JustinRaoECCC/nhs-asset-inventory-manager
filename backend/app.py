from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
from io import BytesIO
import uvicorn

from .services.storage import ensure_dirs, save_json, read_json, clear_json_files
from .services.normalizer import normalize_station_centric, normalize_asset_centric
from .services.comparator import compare_inventories
from .services.report import build_missing_stations_rows, rows_to_excel_bytes
from .models import Inventory

# Project paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
JSON_DIR = DATA_DIR / "json"
FRONTEND_DIR = ROOT / "frontend"

# In-memory session state: compare only works when both set in THIS run.
CURRENT = {"asset_inventory": None, "hydex": None}

app = FastAPI(
    title="NHS Asset Inventory Manager",
    version="1.1.0",
    description="Upload two Excel files, normalize → JSON, visualize, and compare (session-based)."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.on_event("startup")
def _startup():
    ensure_dirs(JSON_DIR)
    # wipe old JSON so a fresh app run has no stale compare state
    clear_json_files(JSON_DIR)
    CURRENT["asset_inventory"] = None
    CURRENT["hydex"] = None

@app.get("/", response_class=HTMLResponse)
def root():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>Frontend not found.</h1>", status_code=500)
    return index.read_text(encoding="utf-8")

@app.post("/api/upload/asset_inventory")
async def upload_asset_inventory(file: UploadFile = File(...)):
    """
    Station-centric Excel: we read the file IN-MEMORY (no disk upload),
    normalize, overwrite JSON, and update session state.
    """
    try:
        content = await file.read()  # bytes; not persisted
        inventory: Inventory = normalize_station_centric(content)
        save_json(inventory, JSON_DIR, filename="asset_inventory.json")  # overwrite
        CURRENT["asset_inventory"] = inventory
        return {"message": "Uploaded & normalized successfully.",
                "inventory": inventory.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process asset inventory: {e}")

@app.post("/api/upload/hydex")
async def upload_hydex(file: UploadFile = File(...)):
    """
    HYDEX-like Excel: in-memory only; normalized & JSON overwritten.
    """
    try:
        content = await file.read()
        inventory: Inventory = normalize_asset_centric(content)
        save_json(inventory, JSON_DIR, filename="hydex.json")  # overwrite
        CURRENT["hydex"] = inventory
        return {"message": "Uploaded & normalized successfully.",
                "inventory": inventory.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process HYDEX file: {e}")

@app.get("/api/json/{name}")
def get_json(name: str):
    """Fetch the saved normalized JSON by name for debugging/inspection."""
    path = JSON_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name}.json not found.")
    return JSONResponse(read_json(path))

@app.get("/api/compare")
def compare():
    """
    Compare ONLY if both files were uploaded in this app session.
    (No stale JSON from disk; enforced by in-memory check.)
    """
    left = CURRENT.get("asset_inventory")
    right = CURRENT.get("hydex")
    if not left or not right:
        raise HTTPException(
            status_code=400,
            detail="Upload both Excel files in this session before comparing."
        )
    return compare_inventories(left, right)

@app.get("/api/missing_stations")
def missing_stations():
    """
    List stations that exist in HYDEX but NOT in Asset Inventory.
    Returns rows with: Station ID | Station Name | Province | Office | Tech Name
    """
    left = CURRENT.get("asset_inventory")
    right = CURRENT.get("hydex")
    if not left or not right:
        raise HTTPException(status_code=400, detail="Upload both Excel files in this session before generating the list.")
    rows = build_missing_stations_rows(left, right)
    return {"rows": rows, "count": len(rows)}

@app.get("/api/export/missing_stations.xlsx")
def export_missing_stations():
    left = CURRENT.get("asset_inventory")
    right = CURRENT.get("hydex")
    if not left or not right:
        raise HTTPException(status_code=400, detail="Upload both Excel files in this session before exporting.")
    rows = build_missing_stations_rows(left, right)
    content = rows_to_excel_bytes(rows)
    return StreamingResponse(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="hydex_only_stations.xlsx"'}
    )

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
