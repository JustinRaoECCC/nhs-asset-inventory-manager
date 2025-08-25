from typing import Dict, Set, List
from ..models import Inventory

def _norm_id(x: str) -> str:
    # Trim whitespace and compare in UPPERCASE
    return str(x or "").strip().upper()

def _assets_by_station(inv: Inventory):
    """
    Return dict keyed by NORMALIZED station id:
      norm_id -> {'orig_id': original id, 'name': station_name, 'assets': set(types)}
    """
    result: Dict[str, Dict] = {}
    for s in inv.stations:
        nid = _norm_id(s.station_id)
        types = {a.type for a in s.assets}
        # prefer the first seen original id/name; keep assets unioned if duplicates exist with different casings
        if nid not in result:
            result[nid] = {"orig_id": s.station_id, "name": s.station_name or "", "assets": set()}
        result[nid]["assets"].update(types)
    return result


def compare_inventories(left: Inventory, right: Inventory):
    """
    Compare asset presence between two normalized inventories.
    Returns a compact diff highlighting discrepancies.
    """
    L = _assets_by_station(left)
    R = _assets_by_station(right)

    stations = sorted(set(L.keys()).union(R.keys()))
    details = []
    with_diff = 0

    for sid in stations:
        la = L.get(sid, {"orig_id": sid, "name": "", "assets": set()})
        ra = R.get(sid, {"orig_id": sid, "name": "", "assets": set()})

        missing_in_left = sorted(list(ra["assets"] - la["assets"]))
        missing_in_right = sorted(list(la["assets"] - ra["assets"]))

        if missing_in_left or missing_in_right:
            with_diff += 1
            details.append({
                # Prefer the left's original id for display; fall back to right
                "station_id": la.get("orig_id") or ra.get("orig_id") or sid,
                "station_name_left": la["name"],
                "station_name_right": ra["name"],
                "source_left": left.source,
                "source_right": right.source,
                "assets_left": sorted(list(la["assets"])),
                "assets_right": sorted(list(ra["assets"])),
                "missing_in_left": missing_in_left,    # assets present in right but missing in left
                "missing_in_right": missing_in_right,  # assets present in left but missing in right
            })

    return {
        "summary": {
            "stations_compared": len(stations),
            "stations_with_discrepancies": with_diff
        },
        "details": details
    }
