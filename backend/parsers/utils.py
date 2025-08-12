import re
import pandas as pd
from typing import Optional, List
from datetime import datetime, date

# --- existing helpers kept ---
ASSET_KEYWORDS = [
    "cableway", "weir", "well", "metering bridge", "bridge", "flume",
    "v-notch", "sluice", "gate", "intake", "structure", "dam", "boom",
    "still well", "stillwell", "stilling well", "station house",
]
TRUTHY_STRINGS = {"yes", "true", "y", "x", "1", "present", "checked"}

def clean_header(h: str) -> str:
    return re.sub(r"\s+", " ", str(h or "")).strip()

def normalize_asset_type(val: str) -> str:
    s = str(val or "").strip().lower()
    s = s.replace("stillwell", "still well").replace("stilling well", "still well")
    return s.title()

def is_boolish_series(s: pd.Series) -> bool:
    sample = s.dropna().astype(str).str.strip().str.lower().unique()
    if len(sample) == 0:
        return False
    ok = 0
    for v in sample:
        if v in TRUTHY_STRINGS or v in {"no", "false", "0", ""}:
            ok += 1
        else:
            try:
                float(v)
                ok += 1
            except:
                return False
    return True

def is_station_id_like(series: pd.Series) -> bool:
    s = series.dropna().astype(str).str.strip()
    if s.empty:
        return False
    alnum_ratio = (s.str.match(r"^[A-Za-z0-9\-_/]+$")).mean()
    if alnum_ratio < 0.9:
        return False
    unique_ratio = s.nunique() / max(len(s), 1)
    return 0.05 < unique_ratio < 0.9

def find_station_id_column(df: pd.DataFrame) -> Optional[str]:
    headers = [clean_header(c) for c in df.columns]
    mapping = dict(zip(df.columns, headers))
    preferred = [
        "station id", "station_id", "stationid", "station number", "station",
        "station code", "site id", "site code", "nhs id"
    ]
    lower_map = {k: v.lower() for k, v in mapping.items()}
    for k, v in lower_map.items():
        if v in preferred:
            return k
        if "station" in v and ("id" in v or "number" in v or v == "station"):
            return k
        if v in {"site id", "site code"}:
            return k
    for col in df.columns:
        if is_station_id_like(df[col]):
            return col
    return None

def find_station_name_column(df: pd.DataFrame) -> Optional[str]:
    lower = {c: clean_header(c).lower() for c in df.columns}
    for k, v in lower.items():
        if v in {"station name", "name", "site name"} or ("station" in v and "name" in v):
            return k
    return None

def candidate_asset_type_columns(df: pd.DataFrame) -> List[str]:
    cands = []
    lower_headers = {c: clean_header(c).lower() for c in df.columns}
    for c, h in lower_headers.items():
        if any(w in h for w in ["asset", "type", "structure", "feature", "component", "equipment"]):
            cands.append(c)
    for c in df.columns:
        s = df[c].dropna().astype(str).str.strip().str.lower()
        if s.empty:
            continue
        uniques = s.unique()
        if 1 < len(uniques) <= 50:
            score = sum(any(k in u for k in ASSET_KEYWORDS) for u in uniques)
            if score >= 2 and c not in cands:
                cands.append(c)
    return cands

# --- new logic for cleaner comparison ---

# Canonical asset detection from column headers (station-centric)
ASSET_PATTERNS = [
    (r"\bcableway\b", "Cableway"),
    (r"\bweir\b", "Weir"),
    (r"\bwell\b", "Well"),
    (r"\bmetering\s*bridge\b", "Metering Bridge"),
    (r"\bbridge\b", "Metering Bridge"),
    (r"\bheli(copter)?\s*pad\b", "Helicopter Pad"),
    (r"\bshelter\b", "Shelter"),
    (r"\bflume\b", "Flume"),
]

# Columns that should NOT become assets even if boolean-ish
EXCLUDE_IN_HEADER = (
    "condition", "status", "service", "in service", "functional",
    "id", "identifier", "type", "material", "owner", "region",
    "date", "installed", "comment", "note"
)

NEGATIVE_STATUSES = {"mothballed", "removed", "inactive", "decommissioned"}

def header_to_asset(header: str) -> Optional[str]:
    s = clean_header(header).lower()
    if any(tok in s for tok in EXCLUDE_IN_HEADER):
        return None
    for pat, canon in ASSET_PATTERNS:
        if re.search(pat, s):
            return canon
    return None

def is_active_status(val) -> bool:
    s = str(val or "").strip().lower()
    if s == "":
        return True  # blank/unknown → treat as present
    return s not in NEGATIVE_STATUSES

def category_to_asset(category: str) -> Optional[str]:
    """Map HYDEX category labels to canonical station-level assets."""
    s = str(category or "").strip().lower()
    if "shelter type" in s: return "Shelter"
    if "well type" in s:    return "Well"
    if "cableway" in s:     return "Cableway"
    if "weir" in s:         return "Weir"
    if "metering bridge" in s or "bridge" in s: return "Metering Bridge"
    # 'Installation Type' etc. are not assets for presence comparison
    return None

# ---- asset-inventory attribute filtering & date coercion ----
_EXCLUDE_ATTR_TIME_TOKENS = ("start time", "completion time")

def should_exclude_station_attr(header: str) -> bool:
    """Ignore noisy time columns in Asset Inventory."""
    s = clean_header(header).lower()
    return any(tok in s for tok in _EXCLUDE_ATTR_TIME_TOKENS)

def coerce_date_only(val):
    """
    Return YYYY-MM-DD for datetime-like values; leave others unchanged.
    Also handles common date-time strings.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return val
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = str(val).strip()
    # Quick exit if no digits
    if not re.search(r"\d", s):
        return val
    dt = pd.to_datetime(s, errors="coerce")
    if pd.notna(dt):
        return dt.date().isoformat()
    return val
