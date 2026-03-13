"""Data models for the West Linn tree canopy inventory."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Neighborhood:
    neighborhood_id: str
    name: str
    area_acres: float
    population: int
    zoning_primary: str
    elevation_ft_avg: int
    watershed: str


@dataclass
class CanopyRecord:
    record_id: str
    neighborhood_id: str
    land_use: str
    area_acres: float
    canopy_acres: float
    canopy_pct: float
    impervious_acres: float
    impervious_pct: float
    open_ground_acres: float
    year_assessed: int


@dataclass
class Species:
    species_id: str
    common_name: str
    scientific_name: str
    native: bool
    prevalence_pct: float
    avg_dbh_in: float
    avg_height_ft: float
    avg_crown_spread_ft: float
    canopy_area_sqft: float
    habitat_value: str
    growth_rate: str
    typical_lifespan_yr: int


@dataclass
class Park:
    park_id: str
    name: str
    neighborhood_id: str
    area_acres: float
    canopy_acres: float
    canopy_pct: float
    park_type: str
    notable_features: str


@dataclass
class EcosystemServices:
    """Annual ecosystem service values for a given canopy area."""

    canopy_acres: float
    stormwater_value: float = 0.0
    air_quality_value: float = 0.0
    carbon_sequestration_value: float = 0.0
    energy_savings_value: float = 0.0
    property_value_increase: float = 0.0

    @property
    def total_annual(self) -> float:
        return (
            self.stormwater_value
            + self.air_quality_value
            + self.carbon_sequestration_value
            + self.energy_savings_value
        )

    @property
    def total_with_property(self) -> float:
        return self.total_annual + self.property_value_increase


@dataclass
class NeighborhoodSummary:
    """Aggregated canopy statistics for a single neighborhood."""

    neighborhood: Neighborhood
    total_canopy_acres: float = 0.0
    total_impervious_acres: float = 0.0
    total_open_ground_acres: float = 0.0
    canopy_pct: float = 0.0
    records: list[CanopyRecord] = field(default_factory=list)
    parks: list[Park] = field(default_factory=list)
    ecosystem_services: EcosystemServices | None = None
