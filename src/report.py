"""Report generation for the West Linn tree canopy inventory."""

from __future__ import annotations

from typing import Sequence

from .models import NeighborhoodSummary, Species, Park, EcosystemServices
from .analysis import (
    canopy_by_land_use,
    canopy_by_watershed,
    citywide_canopy_acres,
    citywide_canopy_pct,
    citywide_total_acres,
    top_canopy_neighborhoods,
    lowest_canopy_neighborhoods,
)
from .ecosystem_services import estimate_services
from .inventory import (
    load_canopy_records,
    load_neighborhoods,
    load_parks,
    load_species,
    native_species,
    invasive_species,
)


def _hr(char: str = "=", width: int = 72) -> str:
    return char * width


def _section(title: str) -> str:
    return f"\n{_hr()}\n  {title}\n{_hr()}\n"


def generate_full_report() -> str:
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    species = load_species()
    parks = load_parks()

    from .analysis import all_neighborhood_summaries

    summaries = all_neighborhood_summaries(neighborhoods, records, parks)

    total_acres = citywide_total_acres(records)
    canopy_acres = citywide_canopy_acres(records)
    canopy_pct = citywide_canopy_pct(records)
    services = estimate_services(canopy_acres)

    lines: list[str] = []

    # Header
    lines.append(_hr("*"))
    lines.append("  CITY OF WEST LINN, OREGON")
    lines.append("  TREE CANOPY INVENTORY REPORT — 2026")
    lines.append(_hr("*"))

    # Executive summary
    lines.append(_section("EXECUTIVE SUMMARY"))
    lines.append(f"  Total city area assessed:    {total_acres:,.1f} acres")
    lines.append(f"  Total tree canopy:           {canopy_acres:,.1f} acres")
    lines.append(f"  Citywide canopy coverage:    {canopy_pct:.1f}%")
    lines.append(f"  Number of neighborhoods:     {len(neighborhoods)}")
    lines.append(f"  Parks and greenspaces:       {len(parks)}")
    lines.append(f"  Species cataloged:           {len(species)}")
    lines.append("")
    lines.append(f"  Estimated annual ecosystem services value: ${services.total_annual:,.0f}")
    lines.append(f"  Estimated property value contribution:     ${services.property_value_increase:,.0f}")

    # Neighborhood breakdown
    lines.append(_section("NEIGHBORHOOD CANOPY COVERAGE"))
    lines.append(f"  {'Neighborhood':<20} {'Area':>8} {'Canopy':>8} {'Cover%':>8} {'Imperv%':>8}")
    lines.append(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for s in sorted(summaries, key=lambda x: x.canopy_pct, reverse=True):
        imp_pct = (
            (s.total_impervious_acres / s.neighborhood.area_acres * 100)
            if s.neighborhood.area_acres
            else 0
        )
        lines.append(
            f"  {s.neighborhood.name:<20} {s.neighborhood.area_acres:>7.0f}ac"
            f" {s.total_canopy_acres:>7.1f}ac"
            f" {s.canopy_pct:>7.1f}%"
            f" {imp_pct:>7.1f}%"
        )

    # Top and bottom
    lines.append(_section("HIGHEST CANOPY COVERAGE"))
    for s in top_canopy_neighborhoods(summaries, 3):
        lines.append(f"  {s.neighborhood.name}: {s.canopy_pct:.1f}%")

    lines.append(_section("LOWEST CANOPY COVERAGE (Priority for Planting)"))
    for s in lowest_canopy_neighborhoods(summaries, 3):
        lines.append(f"  {s.neighborhood.name}: {s.canopy_pct:.1f}%")

    # Land use
    lines.append(_section("CANOPY BY LAND USE"))
    lu = canopy_by_land_use(records)
    lines.append(f"  {'Land Use':<30} {'Area':>8} {'Canopy':>8} {'Pct':>7}")
    lines.append(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*7}")
    for name, vals in sorted(lu.items(), key=lambda x: x[1]["pct"], reverse=True):
        lines.append(
            f"  {name:<30} {vals['area']:>7.0f}ac {vals['canopy']:>7.1f}ac {vals['pct']:>6.1f}%"
        )

    # Watershed
    lines.append(_section("CANOPY BY WATERSHED"))
    ws = canopy_by_watershed(neighborhoods, records)
    for name, vals in sorted(ws.items()):
        lines.append(
            f"  {name}: {vals['canopy']:,.1f} canopy acres "
            f"/ {vals['area']:,.1f} total acres ({vals['pct']:.1f}%)"
        )

    # Species
    lines.append(_section("TREE SPECIES COMPOSITION"))
    natives = native_species(species)
    non_natives = [s for s in species if not s.native]
    native_pct = sum(s.prevalence_pct for s in natives)
    lines.append(f"  Native species: {len(natives)} ({native_pct:.1f}% of canopy)")
    lines.append(f"  Non-native species: {len(non_natives)} ({100 - native_pct:.1f}% of canopy)")
    lines.append("")
    lines.append(f"  {'Species':<25} {'Native':>7} {'Prev%':>7} {'DBH':>5} {'Ht':>5}")
    lines.append(f"  {'-'*25} {'-'*7} {'-'*7} {'-'*5} {'-'*5}")
    for s in sorted(species, key=lambda x: x.prevalence_pct, reverse=True):
        nat = "Yes" if s.native else "No"
        lines.append(
            f"  {s.common_name:<25} {nat:>7} {s.prevalence_pct:>6.1f}% {s.avg_dbh_in:>4.0f}\" {s.avg_height_ft:>4.0f}'"
        )

    # Invasive concern
    invasives = invasive_species(species)
    if invasives:
        lines.append(_section("INVASIVE SPECIES OF CONCERN"))
        for s in invasives:
            lines.append(f"  - {s.common_name} ({s.scientific_name}): {s.prevalence_pct}% prevalence")

    # Parks
    lines.append(_section("PARKS AND GREENSPACES"))
    lines.append(f"  {'Park':<30} {'Acres':>7} {'Canopy':>7} {'Pct':>6}  Type")
    lines.append(f"  {'-'*30} {'-'*7} {'-'*7} {'-'*6}  {'-'*15}")
    for p in sorted(parks, key=lambda x: x.canopy_acres, reverse=True):
        lines.append(
            f"  {p.name:<30} {p.area_acres:>6.0f}ac {p.canopy_acres:>6.1f}ac {p.canopy_pct:>5.0f}%  {p.park_type}"
        )

    # Ecosystem services
    lines.append(_section("ECOSYSTEM SERVICES VALUATION"))
    lines.append(f"  Based on {canopy_acres:,.1f} acres of tree canopy:\n")
    lines.append(f"  Stormwater interception:     ${services.stormwater_value:>12,.0f} /year")
    lines.append(f"  Air quality improvement:     ${services.air_quality_value:>12,.0f} /year")
    lines.append(f"  Carbon sequestration:        ${services.carbon_sequestration_value:>12,.0f} /year")
    lines.append(f"  Energy savings (heat/cool):  ${services.energy_savings_value:>12,.0f} /year")
    lines.append(f"  {'':>31} {'─'*17}")
    lines.append(f"  Total annual services:       ${services.total_annual:>12,.0f} /year")
    lines.append(f"  Property value contribution:  ${services.property_value_increase:>12,.0f} (capitalized)")

    # Recommendations
    lines.append(_section("RECOMMENDATIONS"))
    lowest = lowest_canopy_neighborhoods(summaries, 3)
    lines.append("  1. PRIORITY PLANTING AREAS")
    for s in lowest:
        lines.append(f"     - {s.neighborhood.name} ({s.canopy_pct:.1f}% canopy)")
    lines.append("")
    lines.append("  2. NATIVE SPECIES EMPHASIS")
    lines.append("     Increase native species ratio from current level by prioritizing:")
    lines.append("     - Oregon White Oak (Quercus garryana) in savanna/meadow settings")
    lines.append("     - Douglas Fir (Pseudotsuga menziesii) in forested corridors")
    lines.append("     - Bigleaf Maple (Acer macrophyllum) along streets and parks")
    lines.append("")
    lines.append("  3. INVASIVE SPECIES MANAGEMENT")
    for s in invasives:
        lines.append(f"     - Remove/replace {s.common_name} ({s.prevalence_pct}% of canopy)")
    lines.append("")
    lines.append("  4. CANOPY TARGETS")
    lines.append("     - Citywide goal: 50% canopy coverage (from current {:.1f}%)".format(canopy_pct))
    lines.append("     - All neighborhoods: minimum 40% canopy coverage")
    lines.append("     - Parks and open space: maintain minimum 60% canopy")
    lines.append("")
    lines.append("  5. MONITORING")
    lines.append("     - Reassess canopy coverage every 5 years using LiDAR/aerial imagery")
    lines.append("     - Track net canopy gain/loss per neighborhood annually")

    lines.append(f"\n{_hr('*')}")
    lines.append("  End of Report")
    lines.append(_hr("*"))

    return "\n".join(lines)
