import pandas as pd
from typing import List
from .utils import (
    clean_header, find_station_id_column, find_station_name_column,
    is_boolish_series, header_to_asset, should_exclude_station_attr, coerce_date_only
)
from ..models import Station, Asset

def parse_station_centric(df: pd.DataFrame) -> List[Station]:
    """
    Per-row station sheet:
      - Station ID/name inferred.
      - Only columns whose headers look like known assets AND whose values are boolean-ish
        are treated as asset presence flags.
      - Everything else becomes station attributes.
    """
    df = df.copy()
    df.columns = [clean_header(c) for c in df.columns]

    sid_col = find_station_id_column(df)
    if not sid_col:
        raise ValueError("Could not detect a 'Station ID' column.")
    sname_col = find_station_name_column(df)

    # Identify asset-flag columns (header + boolean-ish values)
    asset_cols = []
    for c in df.columns:
        if c in (sid_col, sname_col):
            continue
        canon = header_to_asset(c)
        if canon and is_boolish_series(df[c]):
            asset_cols.append((c, canon))

    stations: List[Station] = []
    for _, row in df.iterrows():
        sid = str(row[sid_col]).strip()
        if not sid:
            continue
        sname = str(row[sname_col]).strip() if sname_col and pd.notna(row[sname_col]) else None

        # Assets from boolean flags
        assets = []
        for col_name, canon in asset_cols:
            v = str(row[col_name]).strip().lower()
            truthy = v in {"true", "yes", "y", "x", "1", "present"}
            if not truthy:
                try:
                    truthy = float(v) != 0.0
                except:
                    truthy = False
            if truthy:
                assets.append(Asset(type=canon, attributes={}))

        # Attributes = everything else (excluding sid/name, asset flags, and noisy time cols)
        attrs = {}
        for c in df.columns:
            if c == sid_col or any(c == ac for ac, _ in asset_cols):
                continue
            if should_exclude_station_attr(c):
                continue
            val = row[c]
            if pd.isna(val):
                continue
            # Coerce any datetime-like values to date-only
            attrs[c] = coerce_date_only(val)

        stations.append(Station(
            station_id=sid,
            station_name=sname,
            attributes=attrs,
            assets=assets
        ))
    return stations
