from typing import List, Dict, Any
from io import BytesIO
import re

import pandas as pd

from ..models import Inventory, Station

# Heuristic extractors for HYDEX station attributes
def _get_attr(attrs: Dict[str, Any], keys_like: List[str]) -> str | None:
    if not attrs:
        return None
    for k, v in attrs.items():
        k_low = str(k).lower()
        if any(key in k_low for key in keys_like):
            return str(v)
    return None

def _tech_name(attrs: Dict[str, Any]) -> str | None:
    if not attrs:
        return None
    # Prefer explicit first/last name columns
    first = _get_attr(attrs, ["first name", "firstname", "given name"])
    last = _get_attr(attrs, ["last name", "lastname", "surname", "family name"])
    if first or last:
        return " ".join(x for x in [first, last] if x)
    # Otherwise look for generic technician/name fields
    cand = _get_attr(attrs, ["technician", "tech name", "tech", "contact name", "name"])
    return cand

def _province(attrs: Dict[str, Any]) -> str | None:
    return _get_attr(attrs, ["province", "prov"])

def _office(attrs: Dict[str, Any]) -> str | None:
    return _get_attr(attrs, ["office"])

def build_missing_stations_rows(asset_inventory: Inventory, hydex: Inventory) -> List[Dict[str, str]]:
    def norm_id(x: str) -> str:
        # Trim whitespace and compare in UPPERCASE
        return str(x or "").strip().upper()

    left_ids = {norm_id(s.station_id) for s in asset_inventory.stations}

    rows: List[Dict[str, str]] = []
    for s in hydex.stations:
        if norm_id(s.station_id) not in left_ids:
            attrs = s.attributes or {}
            rows.append({
                "station_id": s.station_id,
                "station_name": s.station_name or "",
                "province": _province(attrs) or "",
                "office": _office(attrs) or "",
                "tech_name": _tech_name(attrs) or "",
            })
    # Sort by Station ID for consistency
    rows.sort(key=lambda r: norm_id(r["station_id"]))
    return rows

def rows_to_excel_bytes(rows: List[Dict[str, str]]) -> BytesIO:
    df = pd.DataFrame(rows, columns=["station_id", "station_name", "province", "office", "tech_name"])
    df.rename(columns={
        "station_id":"Station ID",
        "station_name":"Station Name",
        "province":"Province",
        "office":"Office",
        "tech_name":"Tech Name",
    }, inplace=True)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="HYDEX-only Stations")
    buf.seek(0)
    return buf
