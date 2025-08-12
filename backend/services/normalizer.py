from pathlib import Path
from io import BytesIO
import pandas as pd
from ..models import Inventory
from ..parsers.station_centric import parse_station_centric
from ..parsers.asset_centric import parse_asset_centric
from typing import Union

ExcelSrc = Union[Path, str, bytes, BytesIO]

def _read_excel(src: ExcelSrc) -> pd.DataFrame:
    """Accept a path/str/bytes/BytesIO and return a DataFrame."""
    if isinstance(src, bytes):
        return pd.read_excel(BytesIO(src))
    if isinstance(src, BytesIO):
        src.seek(0)
        return pd.read_excel(src)
    return pd.read_excel(src)  # path-like

def normalize_station_centric(src: ExcelSrc) -> Inventory:
    df = _read_excel(src)
    stations = parse_station_centric(df)
    return Inventory(source="asset_inventory", stations=stations)

def normalize_asset_centric(src: ExcelSrc) -> Inventory:
    df = _read_excel(src)
    stations = parse_asset_centric(df)
    return Inventory(source="hydex", stations=stations)
