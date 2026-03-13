"""Tests for data models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import EcosystemServices, Neighborhood, NeighborhoodSummary


def test_ecosystem_services_total():
    es = EcosystemServices(
        canopy_acres=100,
        stormwater_value=1000,
        air_quality_value=500,
        carbon_sequestration_value=300,
        energy_savings_value=200,
        property_value_increase=5000,
    )
    assert es.total_annual == 2000
    assert es.total_with_property == 7000


def test_neighborhood_summary_defaults():
    n = Neighborhood("N01", "Test", 100, 500, "Residential", 300, "Creek")
    s = NeighborhoodSummary(neighborhood=n)
    assert s.total_canopy_acres == 0.0
    assert s.records == []
    assert s.parks == []
