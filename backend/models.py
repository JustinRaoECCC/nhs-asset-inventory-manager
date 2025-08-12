from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime

class Asset(BaseModel):
    """A single 'thing' at a station (e.g., Cableway, Weir)."""
    type: str = Field(..., description="Human-friendly asset type, title-cased.")
    attributes: Dict[str, Any] = Field(default_factory=dict)

class Station(BaseModel):
    """A station node in the tree."""
    station_id: str
    station_name: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    assets: List[Asset] = Field(default_factory=list)

class Inventory(BaseModel):
    """Full normalized representation of an uploaded file."""
    source: str = Field(..., description="asset_inventory | hydex")
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    stations: List[Station] = Field(default_factory=list)
