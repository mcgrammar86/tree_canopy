"""Estimate ecosystem service values from tree canopy coverage.

Dollar values are per-canopy-acre annual estimates derived from USDA i-Tree Eco
model coefficients calibrated for the Pacific Northwest (Portland metro region).
"""

from .models import EcosystemServices

# Per-acre annual values (USD) — Pacific Northwest urban forest averages
STORMWATER_PER_ACRE = 1376.0    # Rainfall interception, reduced runoff
AIR_QUALITY_PER_ACRE = 305.0    # PM2.5, O3, NO2, SO2 removal
CARBON_SEQ_PER_ACRE = 236.0     # Net annual carbon sequestration
ENERGY_SAVINGS_PER_ACRE = 540.0  # Avoided heating/cooling costs
PROPERTY_VALUE_PER_ACRE = 8850.0  # Capitalized property premium


def estimate_services(canopy_acres: float) -> EcosystemServices:
    """Compute ecosystem service values for a given canopy area."""
    return EcosystemServices(
        canopy_acres=canopy_acres,
        stormwater_value=round(canopy_acres * STORMWATER_PER_ACRE, 2),
        air_quality_value=round(canopy_acres * AIR_QUALITY_PER_ACRE, 2),
        carbon_sequestration_value=round(canopy_acres * CARBON_SEQ_PER_ACRE, 2),
        energy_savings_value=round(canopy_acres * ENERGY_SAVINGS_PER_ACRE, 2),
        property_value_increase=round(canopy_acres * PROPERTY_VALUE_PER_ACRE, 2),
    )
