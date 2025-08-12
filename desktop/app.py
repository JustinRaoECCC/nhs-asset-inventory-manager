# desktop/app.py
# Launch FastAPI in a background thread and open a native window with pywebview.

import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

# Ensure the project root (which contains 'backend/') is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the FastAPI app object directly (avoid string import)
from backend.app import app as fastapi_app  # noqa: E402


class Api:
    """
    JS-bridged API available at window.pywebview.api in the frontend.
    Provides a native 'Save As...' for the HYDEX-only stations export.
    """
    def save_missing_stations_excel(self):
        try:
            # Pull current, in-memory inventories from the backend app
            from backend.app import CURRENT
            from backend.services.report import (
                build_missing_stations_rows,
                rows_to_excel_bytes,
            )
            left = CURRENT.get("asset_inventory")
            right = CURRENT.get("hydex")
            if not left or not right:
                return {"ok": False, "error": "Upload both Excel files in this session before exporting."}

            rows = build_missing_stations_rows(left, right)
            if not rows:
                return {"ok": False, "error": "No HYDEX-only stations to export."}

            buf = rows_to_excel_bytes(rows)  # BytesIO

            # Open native Save As dialog
            win = webview.windows[0]
            # NOTE: create_file_dialog returns a list/tuple of selected paths or None
            paths = win.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename="hydex_only_stations.xlsx",
            )
            if not paths:
                return {"ok": False, "cancelled": True}
            path = paths[0] if isinstance(paths, (list, tuple)) else paths
            with open(path, "wb") as f:
                f.write(buf.getvalue())
            return {"ok": True, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def run_server():
    # If port 8000 is already in use, stop any previous run first.
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, reload=False, log_level="info")


if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Give the server a moment to bind the port before opening the window
    time.sleep(0.8)

    webview.create_window(
        "NHS Asset Inventory Manager",
        "http://127.0.0.1:8000",
        width=1280,
        height=860,
        resizable=True,
        js_api=Api(),
    )
    webview.start()
