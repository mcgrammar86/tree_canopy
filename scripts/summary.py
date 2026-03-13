#!/usr/bin/env python3
"""Print a quick canopy inventory summary to stdout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inventory import load_neighborhoods, load_canopy_records, load_parks, load_species, native_species
from src.analysis import (
    all_neighborhood_summaries,
    citywide_canopy_acres,
    citywide_canopy_pct,
    citywide_total_acres,
    top_canopy_neighborhoods,
    lowest_canopy_neighborhoods,
)
from src.ecosystem_services import estimate_services


def main() -> None:
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    parks = load_parks()
    species = load_species()

    total = citywide_total_acres(records)
    canopy = citywide_canopy_acres(records)
    pct = citywide_canopy_pct(records)
    services = estimate_services(canopy)
    summaries = all_neighborhood_summaries(neighborhoods, records, parks)

    print("West Linn, OR — Tree Canopy Summary")
    print("=" * 40)
    print(f"Total area:       {total:,.1f} acres")
    print(f"Tree canopy:      {canopy:,.1f} acres ({pct:.1f}%)")
    print(f"Neighborhoods:    {len(neighborhoods)}")
    print(f"Parks/greenspaces: {len(parks)}")
    print(f"Species tracked:  {len(species)}")
    natives = native_species(species)
    print(f"Native species:   {len(natives)} ({sum(s.prevalence_pct for s in natives):.1f}%)")
    print()

    print("Top canopy neighborhoods:")
    for s in top_canopy_neighborhoods(summaries, 5):
        print(f"  {s.neighborhood.name:<20} {s.canopy_pct:.1f}%")
    print()

    print("Lowest canopy (priority planting):")
    for s in lowest_canopy_neighborhoods(summaries, 5):
        print(f"  {s.neighborhood.name:<20} {s.canopy_pct:.1f}%")
    print()

    print(f"Annual ecosystem services: ${services.total_annual:,.0f}")
    print(f"Property value impact:     ${services.property_value_increase:,.0f}")


if __name__ == "__main__":
    main()
