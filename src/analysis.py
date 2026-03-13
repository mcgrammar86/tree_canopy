"""Canopy coverage analysis for West Linn."""

from typing import Dict, List, Sequence

from .models import (
    CanopyRecord,
    Neighborhood,
    NeighborhoodSummary,
    Park,
)
from .inventory import records_for_neighborhood, parks_for_neighborhood


def citywide_canopy_acres(records: Sequence[CanopyRecord]) -> float:
    return sum(r.canopy_acres for r in records)


def citywide_total_acres(records: Sequence[CanopyRecord]) -> float:
    return sum(r.area_acres for r in records)


def citywide_canopy_pct(records: Sequence[CanopyRecord]) -> float:
    total = citywide_total_acres(records)
    if total == 0:
        return 0.0
    return (citywide_canopy_acres(records) / total) * 100


def canopy_by_land_use(records):
    # type: (Sequence[CanopyRecord]) -> Dict[str, Dict[str, float]]
    """Return canopy stats grouped by land-use category.

    Returns a dict like:
        {"Single-Family Residential": {"area": ..., "canopy": ..., "pct": ...}, ...}
    """
    groups = {}  # type: Dict[str, Dict[str, float]]
    for r in records:
        g = groups.setdefault(r.land_use, {"area": 0.0, "canopy": 0.0})
        g["area"] += r.area_acres
        g["canopy"] += r.canopy_acres
    for g in groups.values():
        g["pct"] = (g["canopy"] / g["area"] * 100) if g["area"] else 0.0
    return groups


def neighborhood_summary(
    neighborhood: Neighborhood,
    records: Sequence[CanopyRecord],
    parks: Sequence[Park],
) -> NeighborhoodSummary:
    nhood_records = records_for_neighborhood(records, neighborhood.neighborhood_id)
    nhood_parks = parks_for_neighborhood(parks, neighborhood.neighborhood_id)
    total_canopy = sum(r.canopy_acres for r in nhood_records)
    total_impervious = sum(r.impervious_acres for r in nhood_records)
    total_open = sum(r.open_ground_acres for r in nhood_records)
    area = neighborhood.area_acres
    pct = (total_canopy / area * 100) if area else 0.0
    return NeighborhoodSummary(
        neighborhood=neighborhood,
        total_canopy_acres=round(total_canopy, 1),
        total_impervious_acres=round(total_impervious, 1),
        total_open_ground_acres=round(total_open, 1),
        canopy_pct=round(pct, 1),
        records=nhood_records,
        parks=nhood_parks,
    )


def all_neighborhood_summaries(
    neighborhoods,  # type: Sequence[Neighborhood]
    records,        # type: Sequence[CanopyRecord]
    parks,          # type: Sequence[Park]
):
    # type: (...) -> List[NeighborhoodSummary]
    return [neighborhood_summary(n, records, parks) for n in neighborhoods]


def top_canopy_neighborhoods(
    summaries,  # type: Sequence[NeighborhoodSummary]
    n=5,        # type: int
):
    # type: (...) -> List[NeighborhoodSummary]
    return sorted(summaries, key=lambda s: s.canopy_pct, reverse=True)[:n]


def lowest_canopy_neighborhoods(
    summaries,  # type: Sequence[NeighborhoodSummary]
    n=5,        # type: int
):
    # type: (...) -> List[NeighborhoodSummary]
    return sorted(summaries, key=lambda s: s.canopy_pct)[:n]


def canopy_by_watershed(neighborhoods, records):
    # type: (Sequence[Neighborhood], Sequence[CanopyRecord]) -> Dict[str, Dict[str, float]]
    """Aggregate canopy statistics by watershed."""
    ws = {}  # type: Dict[str, Dict[str, float]]
    for n in neighborhoods:
        nhood_records = records_for_neighborhood(records, n.neighborhood_id)
        entry = ws.setdefault(n.watershed, {"area": 0.0, "canopy": 0.0})
        entry["area"] += sum(r.area_acres for r in nhood_records)
        entry["canopy"] += sum(r.canopy_acres for r in nhood_records)
    for entry in ws.values():
        entry["pct"] = (entry["canopy"] / entry["area"] * 100) if entry["area"] else 0.0
    return ws
