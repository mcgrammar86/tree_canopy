"""Load and query the West Linn tree canopy inventory data."""

import csv
from pathlib import Path
from typing import List, Optional, Sequence

from .models import CanopyRecord, Neighborhood, Park, Species

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _bool_from_str(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "1")


def load_neighborhoods(path=None):
    # type: (Optional[Path]) -> List[Neighborhood]
    path = path or DATA_DIR / "neighborhoods.csv"
    results = []  # type: List[Neighborhood]
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            results.append(
                Neighborhood(
                    neighborhood_id=row["neighborhood_id"],
                    name=row["name"],
                    area_acres=float(row["area_acres"]),
                    population=int(row["population"]),
                    zoning_primary=row["zoning_primary"],
                    elevation_ft_avg=int(row["elevation_ft_avg"]),
                    watershed=row["watershed"],
                )
            )
    return results


def load_canopy_records(path=None):
    # type: (Optional[Path]) -> List[CanopyRecord]
    path = path or DATA_DIR / "canopy_inventory.csv"
    results = []  # type: List[CanopyRecord]
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            results.append(
                CanopyRecord(
                    record_id=row["record_id"],
                    neighborhood_id=row["neighborhood_id"],
                    land_use=row["land_use"],
                    area_acres=float(row["area_acres"]),
                    canopy_acres=float(row["canopy_acres"]),
                    canopy_pct=float(row["canopy_pct"]),
                    impervious_acres=float(row["impervious_acres"]),
                    impervious_pct=float(row["impervious_pct"]),
                    open_ground_acres=float(row["open_ground_acres"]),
                    year_assessed=int(row["year_assessed"]),
                )
            )
    return results


def load_species(path=None):
    # type: (Optional[Path]) -> List[Species]
    path = path or DATA_DIR / "species_catalog.csv"
    results = []  # type: List[Species]
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            lifespan = row["typical_lifespan_yr"]
            results.append(
                Species(
                    species_id=row["species_id"],
                    common_name=row["common_name"],
                    scientific_name=row["scientific_name"],
                    native=_bool_from_str(row["native"]),
                    prevalence_pct=float(row["prevalence_pct"]),
                    avg_dbh_in=float(row["avg_dbh_in"]),
                    avg_height_ft=float(row["avg_height_ft"]),
                    avg_crown_spread_ft=float(row["avg_crown_spread_ft"]),
                    canopy_area_sqft=float(row["canopy_area_sqft"]),
                    habitat_value=row["habitat_value"],
                    growth_rate=row["growth_rate"],
                    typical_lifespan_yr=int(lifespan) if lifespan.isdigit() else 0,
                )
            )
    return results


def load_parks(path=None):
    # type: (Optional[Path]) -> List[Park]
    path = path or DATA_DIR / "parks_greenspaces.csv"
    results = []  # type: List[Park]
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            results.append(
                Park(
                    park_id=row["park_id"],
                    name=row["name"],
                    neighborhood_id=row["neighborhood_id"],
                    area_acres=float(row["area_acres"]),
                    canopy_acres=float(row["canopy_acres"]),
                    canopy_pct=float(row["canopy_pct"]),
                    park_type=row["type"],
                    notable_features=row["notable_features"],
                )
            )
    return results


def records_for_neighborhood(records, neighborhood_id):
    # type: (Sequence[CanopyRecord], str) -> List[CanopyRecord]
    return [r for r in records if r.neighborhood_id == neighborhood_id]


def parks_for_neighborhood(parks, neighborhood_id):
    # type: (Sequence[Park], str) -> List[Park]
    return [p for p in parks if p.neighborhood_id == neighborhood_id]


def native_species(species):
    # type: (Sequence[Species]) -> List[Species]
    return [s for s in species if s.native]


def invasive_species(species):
    # type: (Sequence[Species]) -> List[Species]
    return [s for s in species if not s.native and s.habitat_value.startswith("Low")]
