#!/usr/bin/env python3
"""Generate the full West Linn tree canopy inventory report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.report import generate_full_report


def main() -> None:
    report = generate_full_report()
    print(report)


if __name__ == "__main__":
    main()
