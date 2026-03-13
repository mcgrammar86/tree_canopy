"""Tests for canopy analysis functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inventory import load_neighborhoods, load_canopy_records, load_parks
from src.analysis import (
    all_neighborhood_summaries,
    canopy_by_land_use,
    canopy_by_watershed,
    citywide_canopy_acres,
    citywide_canopy_pct,
    citywide_total_acres,
    top_canopy_neighborhoods,
    lowest_canopy_neighborhoods,
)
from src.ecosystem_services import estimate_services


def test_citywide_totals():
    records = load_canopy_records()
    total = citywide_total_acres(records)
    canopy = citywide_canopy_acres(records)
    pct = citywide_canopy_pct(records)
    assert total > 4000
    assert canopy > 1500
    assert 30 < pct < 60


def test_canopy_by_land_use():
    records = load_canopy_records()
    lu = canopy_by_land_use(records)
    assert "Single-Family Residential" in lu
    assert "Parks/Open Space" in lu
    assert lu["Parks/Open Space"]["pct"] > lu["Commercial"]["pct"]


def test_neighborhood_summaries():
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    parks = load_parks()
    summaries = all_neighborhood_summaries(neighborhoods, records, parks)
    assert len(summaries) == 10
    for s in summaries:
        assert s.canopy_pct > 0


def test_top_and_lowest():
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    parks = load_parks()
    summaries = all_neighborhood_summaries(neighborhoods, records, parks)
    top = top_canopy_neighborhoods(summaries, 3)
    low = lowest_canopy_neighborhoods(summaries, 3)
    assert top[0].canopy_pct >= top[-1].canopy_pct
    assert low[0].canopy_pct <= low[-1].canopy_pct


def test_canopy_by_watershed():
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    ws = canopy_by_watershed(neighborhoods, records)
    assert "Willamette River" in ws
    assert "Tualatin River" in ws
    assert "Tanner Creek" in ws


def test_ecosystem_services():
    records = load_canopy_records()
    canopy = citywide_canopy_acres(records)
    services = estimate_services(canopy)
    assert services.stormwater_value > 0
    assert services.total_annual > 0
