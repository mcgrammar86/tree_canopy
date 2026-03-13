"""Tests for inventory data loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inventory import (
    load_neighborhoods,
    load_canopy_records,
    load_species,
    load_parks,
    native_species,
    invasive_species,
    records_for_neighborhood,
    parks_for_neighborhood,
)


def test_load_neighborhoods():
    neighborhoods = load_neighborhoods()
    assert len(neighborhoods) == 10
    names = {n.name for n in neighborhoods}
    assert "Bolton" in names
    assert "Willamette" in names


def test_load_canopy_records():
    records = load_canopy_records()
    assert len(records) > 0
    assert all(r.canopy_pct >= 0 for r in records)


def test_load_species():
    species = load_species()
    assert len(species) == 20
    df = species[0]
    assert df.common_name == "Douglas Fir"
    assert df.native is True


def test_load_parks():
    parks = load_parks()
    assert len(parks) == 18
    assert any(p.name == "Mary S. Young State Park" for p in parks)


def test_native_species():
    species = load_species()
    natives = native_species(species)
    assert all(s.native for s in natives)
    assert len(natives) > 0


def test_invasive_species():
    species = load_species()
    invasives = invasive_species(species)
    assert all(not s.native for s in invasives)


def test_records_for_neighborhood():
    records = load_canopy_records()
    bolton = records_for_neighborhood(records, "N01")
    assert len(bolton) > 0
    assert all(r.neighborhood_id == "N01" for r in bolton)


def test_parks_for_neighborhood():
    parks = load_parks()
    willamette_parks = parks_for_neighborhood(parks, "N07")
    assert len(willamette_parks) > 0
