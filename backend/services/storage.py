from pathlib import Path
from datetime import datetime, date
import json

import pandas as pd
import numpy as np

def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def _json_default(o):
    # Datetime-like → date-only ISO (YYYY-MM-DD)
    if isinstance(o, (pd.Timestamp, datetime)):
        try:
            return o.date().isoformat()
        except Exception:
            return str(o)
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_)):
        return bool(o)
    return str(o)

def save_json(data_obj, dest_dir: Path, filename: str) -> Path:
    """Overwrite JSON on every call."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / filename
    payload = data_obj.model_dump() if hasattr(data_obj, "model_dump") else data_obj
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default, allow_nan=False)
    return out

def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def clear_json_files(dest_dir: Path, names=("asset_inventory.json", "hydex.json")):
    """Remove any old JSON so a fresh run has no stale state."""
    for n in names:
        p = dest_dir / n
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
