# West Linn, Oregon — Tree Canopy Inventory

A comprehensive tree canopy inventory and analysis system for the City of West Linn, Oregon (Clackamas County). This project catalogs urban tree canopy coverage across the city's neighborhoods, estimates ecosystem services, and provides tools for planning and management.

## Overview

- **City**: West Linn, Oregon
- **Area**: ~7.4 square miles (4,736 acres)
- **Population**: ~27,000 (2020 Census)
- **Estimated Tree Canopy Coverage**: ~43% (2,035 acres)
- **Inventory Year**: 2026

## Project Structure

```
tree_canopy/
├── README.md
├── requirements.txt
├── data/
│   ├── neighborhoods.csv          # Neighborhood boundaries and metadata
│   ├── canopy_inventory.csv       # Tree canopy coverage by zone
│   ├── species_catalog.csv        # Common tree species in West Linn
│   └── parks_greenspaces.csv      # Parks and public greenspace data
├── src/
│   ├── __init__.py
│   ├── models.py                  # Data models for inventory records
│   ├── inventory.py               # Core inventory loading and queries
│   ├── analysis.py                # Canopy coverage analysis
│   ├── ecosystem_services.py      # Ecosystem service value estimates
│   └── report.py                  # Report generation
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_inventory.py
│   └── test_analysis.py
└── scripts/
    ├── generate_report.py         # Generate a full canopy report
    └── summary.py                 # Print a quick summary to stdout
```

## Neighborhoods Covered

West Linn is divided into several distinct neighborhoods, each with unique canopy characteristics:

| Neighborhood | Acres | Canopy % | Character |
|---|---|---|---|
| Bolton | 480 | 38% | Mixed residential/commercial |
| Hidden Springs | 520 | 52% | Wooded hillside residential |
| Marylhurst | 390 | 48% | Historic campus area |
| Robinwood | 610 | 40% | River-adjacent residential |
| Sunset | 450 | 35% | Newer development |
| Savanna Oaks | 380 | 44% | Native oak habitat |
| Willamette | 560 | 50% | Riverfront, mature canopy |
| Tanner Basin | 500 | 46% | Forested creek corridor |
| Parker Crest | 420 | 37% | Hilltop residential |
| Bland Circle | 426 | 42% | Central mixed-use |

## Quick Start

```bash
pip install -r requirements.txt
python scripts/summary.py
python scripts/generate_report.py
```

## Ecosystem Services

The inventory estimates annual ecosystem service values provided by West Linn's tree canopy:

- **Stormwater interception**: ~$2.8M/year
- **Air quality improvement**: ~$620K/year
- **Carbon sequestration**: ~$480K/year
- **Energy savings** (heating/cooling): ~$1.1M/year
- **Property value increase**: ~$18M (capitalized)

## Data Sources

- City of West Linn GIS data
- Oregon Department of Forestry Urban Canopy Assessment
- USDA i-Tree Eco model coefficients
- National Land Cover Database (NLCD)
- Metro Regional Land Information System (RLIS)

## License

This project is released under the MIT License.
