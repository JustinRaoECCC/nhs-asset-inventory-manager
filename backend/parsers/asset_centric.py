import re
import pandas as pd
from typing import List, Dict
from .utils import (
    clean_header, find_station_id_column, find_station_name_column,
    category_to_asset, is_active_status, coerce_date_only
)
from ..models import Station, Asset

def parse_asset_centric(df: pd.DataFrame) -> List[Station]:
    """
    Asset-centric (HYDEX-like):
      - Rows are category/value/status (e.g., 'SHELTER TYPE' / 'STEEL LOOK-IN' / 'ACTIVE').
      - Map categories to canonical assets; ignore non-asset categories (e.g., 'Installation Type').
      - Only count assets whose status is not mothballed/removed/inactive.
    """
    df = df.copy()
    df.columns = [clean_header(c) for c in df.columns]

    sid_col = find_station_id_column(df)
    if not sid_col:
        raise ValueError("Could not detect a 'Station ID' column in HYDEX.")
    sname_col = find_station_name_column(df)

    lower = {c: c.lower() for c in df.columns}

    # category column: contains "type" or "category"
    cat_cols = [c for c in df.columns if re.search(r"\b(type|category)\b", lower[c])]
    category_col = cat_cols[0] if cat_cols else None
    if not category_col:
        raise ValueError("Could not infer a HYDEX 'category/type' column.")

    # heuristic: value column is the next column after category
    value_col = None
    try:
        idx = list(df.columns).index(category_col)
        if idx + 1 < len(df.columns):
            value_col = df.columns[idx + 1]
    except ValueError:
        pass

    status_col = next((c for c in df.columns if "status" in lower[c]), None)
    date_col   = next((c for c in df.columns if "date" in lower[c]), None)
    note_col   = next((c for c in df.columns if any(k in lower[c] for k in ["comment", "note", "remark"])), None)

    grouped: Dict[str, Dict] = {}

    for _, row in df.iterrows():
        sid = str(row[sid_col]).strip()
        if not sid:
            continue
        sname = str(row[sname_col]).strip() if sname_col and pd.notna(row[sname_col]) else None

        cat = row[category_col] if category_col in df.columns else None
        asset_name = category_to_asset(cat)
        if not asset_name:
            # Not a station-level asset (e.g., "Installation Type") → skip for presence
            continue

        status_val = row[status_col] if status_col in df.columns else None
        if not is_active_status(status_val):
            # MOTHBALLED/REMOVED/INACTIVE → do not count as present
            continue

        attrs = {}
        if value_col in df.columns and pd.notna(row[value_col]):
            attrs["value"] = row[value_col]
        if status_col and status_col in df.columns and pd.notna(row[status_col]):
            attrs["status"] = row[status_col]
        if date_col and date_col in df.columns and pd.notna(row[date_col]):
            attrs["date"] = coerce_date_only(row[date_col])
        if note_col and note_col in df.columns and pd.notna(row[note_col]):
            attrs["note"] = row[note_col]

        if sid not in grouped:
            grouped[sid] = {"station_name": sname, "attributes": {}, "assets": {}}
        if sname and not grouped[sid]["station_name"]:
            grouped[sid]["station_name"] = sname

        grouped[sid]["assets"].setdefault(asset_name, {}).update(attrs)

    def is_lat_col(name: str) -> bool:
        n = name.lower()
        return "lat" in n and "plate" not in n  # avoid false positives

    def is_lon_col(name: str) -> bool:
        n = name.lower()
        return ("lon" in n or "long" in n or "lng" in n) and "length" not in n

    known_cols = {sid_col, sname_col, category_col, value_col, status_col, date_col, note_col}
    station_attr_candidates = [c for c in df.columns if c not in known_cols]

    for sid, gdf in df.groupby(sid_col):
        if sid not in grouped:
            # If we saw no assets for this station, still create a node so attributes show up
            sname = None
            if sname_col and sname_col in gdf.columns:
                svals = gdf[sname_col].dropna()
                sname = None if svals.empty else str(svals.iloc[0]).strip() or None
            grouped[sid] = {"station_name": sname, "attributes": {}, "assets": {}}

        attrs: Dict[str, object] = {}
        for col in station_attr_candidates:
            series = gdf[col].dropna()
            if series.empty:
                continue

            # Latitude / Longitude: average, rounded
            if is_lat_col(col) or is_lon_col(col):
                nums = pd.to_numeric(series, errors="coerce").dropna()
                if not nums.empty:
                    attrs[col] = round(float(nums.mean()), 6)
                continue

            uniques = series.unique()
            if len(uniques) == 1:
                v = uniques[0]
                # If it's a date-ish column, coerce to date-only
                attrs[col] = coerce_date_only(v) if "date" in col.lower() else v
                continue

            # Otherwise use a clear mode if it dominates
            vc = series.value_counts(dropna=True)
            if not vc.empty and vc.iloc[0] >= max(2, 0.6 * vc.sum()):
                v = vc.index[0]
                attrs[col] = coerce_date_only(v) if "date" in col.lower() else v
                continue
            # else: conflicting values across rows → skip

        grouped[sid]["attributes"] = attrs

    stations: List[Station] = []
    for sid, payload in grouped.items():
        assets = [Asset(type=k, attributes=v) for k, v in payload["assets"].items()]
        stations.append(Station(
            station_id=sid,
            station_name=payload["station_name"],
            attributes=payload["attributes"],
            assets=assets
        ))
    return stations
