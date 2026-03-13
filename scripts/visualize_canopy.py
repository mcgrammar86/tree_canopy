#!/usr/bin/env python3
"""
West Linn Tree Canopy Visualization
====================================
Generates a multi-panel figure simulating satellite imagery (NDVI) and
LiDAR-derived canopy height models for each West Linn neighborhood,
overlaid with inventory statistics.

Outputs:  output/west_linn_canopy_dashboard.png

The raster surfaces are procedurally generated from the real inventory
data (canopy %, land-use mix, elevation, species composition) so the
spatial patterns are representative even though pixel positions are
synthetic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

from src.inventory import (
    load_neighborhoods,
    load_canopy_records,
    load_parks,
    load_species,
    native_species,
)
from src.analysis import (
    all_neighborhood_summaries,
    canopy_by_land_use,
    citywide_canopy_acres,
    citywide_canopy_pct,
    citywide_total_acres,
)
from src.ecosystem_services import estimate_services

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
GRID = 400          # pixels per side for raster panels
DPI = 150
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Approximate neighbourhood bounding boxes (row_start, row_end, col_start, col_end)
# laid out on a 400x400 grid to loosely mirror West Linn geography:
#   - north (top)  = Willamette River edge
#   - south (bottom) = hills / Tualatin River
#   - west (left)  = I-205 corridor
#   - east (right) = Wilderness Park / Hidden Springs
NHOOD_BOXES = {
    "N07": (10,  110, 180, 340),   # Willamette      (NE riverfront)
    "N04": (10,  120, 20,  180),   # Robinwood        (NW riverfront)
    "N01": (120, 210, 10,  140),   # Bolton           (W central)
    "N10": (120, 210, 140, 260),   # Bland Circle     (central)
    "N03": (110, 200, 260, 390),   # Marylhurst       (E central)
    "N05": (210, 300, 10,  140),   # Sunset           (SW)
    "N06": (210, 300, 140, 260),   # Savanna Oaks     (S central)
    "N08": (200, 300, 260, 390),   # Tanner Basin     (SE)
    "N09": (300, 390, 140, 260),   # Parker Crest     (S)
    "N02": (300, 390, 260, 390),   # Hidden Springs   (SE hills)
}

# ---------------------------------------------------------------------------
# Helpers — procedural raster generation
# ---------------------------------------------------------------------------

def _make_perlin_like(rows, cols, scale=40, rng=None):
    """Quick smooth noise via upsampled random grid + gaussian blur."""
    if rng is None:
        rng = np.random.default_rng(SEED)
    small_r = max(rows // scale, 2)
    small_c = max(cols // scale, 2)
    # low-res random field
    lo = rng.random((small_r, small_c)).astype(np.float32)
    # bilinear upsample with numpy (no scipy dependency)
    from numpy import interp as _interp
    row_idx = np.linspace(0, small_r - 1, rows)
    col_idx = np.linspace(0, small_c - 1, cols)
    # interpolate rows then columns
    tmp = np.zeros((rows, small_c), dtype=np.float32)
    for c in range(small_c):
        tmp[:, c] = np.interp(row_idx, np.arange(small_r), lo[:, c])
    out = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        out[r, :] = np.interp(col_idx, np.arange(small_c), tmp[r, :])
    return out


def _generate_ndvi(summaries, rng):
    """Build a synthetic NDVI raster (0-1). High canopy → high NDVI."""
    base = _make_perlin_like(GRID, GRID, scale=30, rng=rng) * 0.15
    ndvi = np.full((GRID, GRID), 0.25, dtype=np.float32)  # bare default

    for s in summaries:
        nid = s.neighborhood.neighborhood_id
        if nid not in NHOOD_BOXES:
            continue
        r0, r1, c0, c1 = NHOOD_BOXES[nid]
        h, w = r1 - r0, c1 - c0
        canopy_frac = s.canopy_pct / 100.0

        # base NDVI proportional to canopy
        patch = rng.normal(loc=canopy_frac * 0.85, scale=0.10, size=(h, w)).astype(np.float32)

        # add park hotspots (higher NDVI)
        for park in s.parks:
            pr = rng.integers(2, max(h - 4, 3))
            pc = rng.integers(2, max(w - 4, 3))
            radius = int(np.sqrt(park.area_acres) * 1.5) + 2
            yr, xr = np.ogrid[-pr:h - pr, -pc:w - pc]
            mask = (yr * yr + xr * xr) <= radius * radius
            patch[mask] += 0.12

        # impervious areas (lower NDVI)
        imp_frac = s.total_impervious_acres / s.neighborhood.area_acres
        imp_mask = rng.random((h, w)) < imp_frac * 0.6
        patch[imp_mask] -= 0.25

        ndvi[r0:r1, c0:c1] = patch

    ndvi += base
    return np.clip(ndvi, 0.0, 1.0)


def _generate_chm(summaries, rng):
    """Build a synthetic Canopy Height Model in feet (0-160)."""
    base = _make_perlin_like(GRID, GRID, scale=25, rng=rng) * 8
    chm = np.full((GRID, GRID), 0.0, dtype=np.float32)

    for s in summaries:
        nid = s.neighborhood.neighborhood_id
        if nid not in NHOOD_BOXES:
            continue
        r0, r1, c0, c1 = NHOOD_BOXES[nid]
        h, w = r1 - r0, c1 - c0
        canopy_frac = s.canopy_pct / 100.0

        # place individual "trees" as gaussian blobs
        n_trees = int(canopy_frac * h * w * 0.08)
        patch = np.zeros((h, w), dtype=np.float32)
        for _ in range(n_trees):
            ty = rng.integers(0, h)
            tx = rng.integers(0, w)
            tree_h = rng.normal(loc=70 * canopy_frac + 30, scale=25)
            tree_h = np.clip(tree_h, 10, 155)
            spread = rng.integers(2, 5)
            y0 = max(ty - spread, 0)
            y1 = min(ty + spread + 1, h)
            x0 = max(tx - spread, 0)
            x1 = min(tx + spread + 1, w)
            yr = np.arange(y0, y1)[:, None]
            xr = np.arange(x0, x1)[None, :]
            gauss = tree_h * np.exp(-((yr - ty) ** 2 + (xr - tx) ** 2) / (2 * spread))
            patch[y0:y1, x0:x1] = np.maximum(patch[y0:y1, x0:x1], gauss)

        # parks get taller, denser trees
        for park in s.parks:
            pr = rng.integers(3, max(h - 5, 4))
            pc = rng.integers(3, max(w - 5, 4))
            radius = int(np.sqrt(park.area_acres) * 1.5) + 3
            for _ in range(int(park.canopy_acres * 0.5)):
                ty = int(np.clip(rng.normal(pr, radius * 0.4), 0, h - 1))
                tx = int(np.clip(rng.normal(pc, radius * 0.4), 0, w - 1))
                tree_h = rng.normal(loc=95, scale=20)
                tree_h = np.clip(tree_h, 40, 155)
                spread = rng.integers(2, 5)
                y0 = max(ty - spread, 0)
                y1 = min(ty + spread + 1, h)
                x0 = max(tx - spread, 0)
                x1 = min(tx + spread + 1, w)
                yr = np.arange(y0, y1)[:, None]
                xr = np.arange(x0, x1)[None, :]
                gauss = tree_h * np.exp(-((yr - ty) ** 2 + (xr - tx) ** 2) / (2 * spread))
                patch[y0:y1, x0:x1] = np.maximum(patch[y0:y1, x0:x1], gauss)

        chm[r0:r1, c0:c1] = patch

    chm += base
    chm[chm < 0] = 0
    return np.clip(chm, 0, 160)


def _generate_elevation(neighborhoods, rng):
    """Build a synthetic DEM surface using neighbourhood elevation data."""
    dem = _make_perlin_like(GRID, GRID, scale=50, rng=rng) * 40 + 200
    for n in neighborhoods:
        nid = n.neighborhood_id
        if nid not in NHOOD_BOXES:
            continue
        r0, r1, c0, c1 = NHOOD_BOXES[nid]
        h, w = r1 - r0, c1 - c0
        patch = rng.normal(loc=n.elevation_ft_avg, scale=30, size=(h, w)).astype(np.float32)
        # smooth blend
        dem[r0:r1, c0:c1] = dem[r0:r1, c0:c1] * 0.2 + patch * 0.8
    return dem


def _generate_landcover(summaries, rng):
    """Build a classified land cover raster.  Classes:
       0=water, 1=impervious, 2=bare/grass, 3=shrub, 4=canopy
    """
    lc = np.full((GRID, GRID), 2, dtype=np.int8)  # default = open ground
    # water along north edge (Willamette River)
    lc[0:8, :] = 0

    for s in summaries:
        nid = s.neighborhood.neighborhood_id
        if nid not in NHOOD_BOXES:
            continue
        r0, r1, c0, c1 = NHOOD_BOXES[nid]
        h, w = r1 - r0, c1 - c0

        canopy_frac = s.canopy_pct / 100.0
        imp_frac = s.total_impervious_acres / s.neighborhood.area_acres

        draw = rng.random((h, w))
        patch = np.full((h, w), 2, dtype=np.int8)
        patch[draw < canopy_frac] = 4
        patch[(draw >= canopy_frac) & (draw < canopy_frac + imp_frac)] = 1
        remaining = (draw >= canopy_frac + imp_frac)
        patch[remaining & (rng.random((h, w)) < 0.3)] = 3  # shrub

        lc[r0:r1, c0:c1] = patch

    return lc


# ---------------------------------------------------------------------------
# Custom colormaps
# ---------------------------------------------------------------------------

def _ndvi_cmap():
    colors = [
        (0.65, 0.55, 0.40),  # bare soil / brown
        (0.85, 0.82, 0.60),  # dry grass
        (0.55, 0.75, 0.30),  # light vegetation
        (0.20, 0.60, 0.15),  # moderate vegetation
        (0.05, 0.40, 0.05),  # dense canopy
        (0.00, 0.27, 0.00),  # very dense canopy
    ]
    return LinearSegmentedColormap.from_list("ndvi", colors, N=256)


def _chm_cmap():
    colors = [
        (0.90, 0.88, 0.82),  # ground
        (0.75, 0.85, 0.45),  # low shrub
        (0.40, 0.72, 0.25),  # small tree
        (0.15, 0.55, 0.12),  # medium tree
        (0.05, 0.38, 0.08),  # tall tree
        (0.02, 0.22, 0.02),  # very tall (old growth)
    ]
    return LinearSegmentedColormap.from_list("chm", colors, N=256)


def _landcover_cmap():
    cmap = mcolors.ListedColormap([
        "#2B6CA3",  # 0 water
        "#B0B0B0",  # 1 impervious
        "#D4C87A",  # 2 bare/grass
        "#8DB86E",  # 3 shrub
        "#1B6E1B",  # 4 canopy
    ])
    return cmap


# ---------------------------------------------------------------------------
# Main figure
# ---------------------------------------------------------------------------

def build_dashboard():
    neighborhoods = load_neighborhoods()
    records = load_canopy_records()
    parks = load_parks()
    species = load_species()
    summaries = all_neighborhood_summaries(neighborhoods, records, parks)

    total_acres = citywide_total_acres(records)
    canopy_acres = citywide_canopy_acres(records)
    canopy_pct = citywide_canopy_pct(records)
    services = estimate_services(canopy_acres)

    rng = np.random.default_rng(SEED)

    # Generate rasters
    ndvi = _generate_ndvi(summaries, rng)
    chm = _generate_chm(summaries, rng)
    dem = _generate_elevation(neighborhoods, rng)
    lc = _generate_landcover(summaries, rng)

    # -----------------------------------------------------------------------
    # Build the figure: 3 rows x 3 cols
    #   Top row:    NDVI (large, spans 2 cols)  |  Canopy bar chart
    #   Mid row:    LiDAR CHM (large, 2 cols)   |  Land-use pie
    #   Bot row:    Land cover  |  Elevation  |  Stats text
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(20, 22), facecolor="#1a1a2e")
    gs = gridspec.GridSpec(
        3, 3,
        height_ratios=[1, 1, 0.85],
        width_ratios=[1, 1, 0.9],
        hspace=0.28, wspace=0.25,
        left=0.05, right=0.95, top=0.93, bottom=0.03,
    )

    title_color = "#e0e0e0"
    label_color = "#c0c0c0"
    fig.suptitle(
        "WEST LINN, OREGON  —  TREE CANOPY INVENTORY 2026\n"
        "Satellite NDVI & LiDAR Canopy Height Analysis",
        fontsize=22, fontweight="bold", color=title_color, y=0.97,
    )

    # --- Panel 1: NDVI (top-left, 2 cols) ---------------------------------
    ax_ndvi = fig.add_subplot(gs[0, 0:2])
    im_ndvi = ax_ndvi.imshow(ndvi, cmap=_ndvi_cmap(), vmin=0, vmax=1, aspect="equal")
    _overlay_boundaries(ax_ndvi, summaries, label_color)
    ax_ndvi.set_title("Simulated Satellite NDVI", fontsize=14,
                       fontweight="bold", color=title_color, pad=10)
    ax_ndvi.axis("off")
    cb1 = plt.colorbar(im_ndvi, ax=ax_ndvi, fraction=0.03, pad=0.01)
    cb1.set_label("NDVI", color=label_color, fontsize=10)
    cb1.ax.tick_params(colors=label_color, labelsize=8)

    # --- Panel 2: Neighborhood bar chart (top-right) -----------------------
    ax_bar = fig.add_subplot(gs[0, 2])
    ax_bar.set_facecolor("#1a1a2e")
    sorted_s = sorted(summaries, key=lambda s: s.canopy_pct)
    names = [s.neighborhood.name for s in sorted_s]
    pcts = [s.canopy_pct for s in sorted_s]
    colors_bar = [plt.cm.YlGn(p / 65.0) for p in pcts]
    bars = ax_bar.barh(names, pcts, color=colors_bar, edgecolor="#333333", linewidth=0.5)
    ax_bar.axvline(x=canopy_pct, color="#ff6b6b", linestyle="--", linewidth=1.5, alpha=0.8)
    ax_bar.text(canopy_pct + 0.5, len(names) - 0.5,
                "City avg\n{:.1f}%".format(canopy_pct),
                color="#ff6b6b", fontsize=8, va="top")
    for i, (bar, pct) in enumerate(zip(bars, pcts)):
        ax_bar.text(pct + 0.5, i, "{:.1f}%".format(pct),
                    va="center", fontsize=8, color=label_color)
    ax_bar.set_xlabel("Canopy Coverage %", color=label_color, fontsize=10)
    ax_bar.set_title("Neighborhood Canopy Coverage", fontsize=13,
                      fontweight="bold", color=title_color, pad=10)
    ax_bar.tick_params(colors=label_color, labelsize=9)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    for spine in ax_bar.spines.values():
        spine.set_color("#444444")
    ax_bar.set_xlim(0, 70)

    # --- Panel 3: LiDAR CHM (mid-left, 2 cols) ----------------------------
    ax_chm = fig.add_subplot(gs[1, 0:2])
    im_chm = ax_chm.imshow(chm, cmap=_chm_cmap(), vmin=0, vmax=150, aspect="equal")
    _overlay_boundaries(ax_chm, summaries, label_color)
    ax_chm.set_title("Simulated LiDAR Canopy Height Model (CHM)", fontsize=14,
                      fontweight="bold", color=title_color, pad=10)
    ax_chm.axis("off")
    cb2 = plt.colorbar(im_chm, ax=ax_chm, fraction=0.03, pad=0.01)
    cb2.set_label("Height (ft)", color=label_color, fontsize=10)
    cb2.ax.tick_params(colors=label_color, labelsize=8)

    # --- Panel 4: Land-use pie chart (mid-right) ---------------------------
    ax_pie = fig.add_subplot(gs[1, 2])
    ax_pie.set_facecolor("#1a1a2e")
    lu = canopy_by_land_use(records)
    lu_names = []
    lu_canopy = []
    for name in sorted(lu.keys(), key=lambda k: lu[k]["canopy"], reverse=True):
        lu_names.append(name)
        lu_canopy.append(lu[name]["canopy"])
    pie_colors = ["#2d6a4f", "#40916c", "#52b788", "#74c69d", "#95d5b2", "#b7e4c7", "#d8f3dc"]
    wedges, texts, autotexts = ax_pie.pie(
        lu_canopy, labels=None, autopct="%1.0f%%",
        colors=pie_colors[:len(lu_canopy)],
        pctdistance=0.78, startangle=140,
        textprops={"fontsize": 9, "color": "#222222"},
    )
    ax_pie.legend(
        wedges, lu_names, loc="lower center",
        fontsize=8, frameon=False,
        bbox_to_anchor=(0.5, -0.08),
        labelcolor=label_color,
        ncol=2,
    )
    ax_pie.set_title("Canopy Distribution by Land Use", fontsize=13,
                      fontweight="bold", color=title_color, pad=10)

    # --- Panel 5: Land cover classification (bottom-left) ------------------
    ax_lc = fig.add_subplot(gs[2, 0])
    ax_lc.imshow(lc, cmap=_landcover_cmap(), vmin=0, vmax=4, aspect="equal",
                 interpolation="nearest")
    ax_lc.set_title("Land Cover Classification", fontsize=13,
                     fontweight="bold", color=title_color, pad=10)
    ax_lc.axis("off")
    lc_labels = ["Water", "Impervious", "Bare / Grass", "Shrub", "Tree Canopy"]
    lc_colors_hex = ["#2B6CA3", "#B0B0B0", "#D4C87A", "#8DB86E", "#1B6E1B"]
    patches = [mpatches.Patch(color=c, label=l) for c, l in zip(lc_colors_hex, lc_labels)]
    ax_lc.legend(handles=patches, loc="lower center", fontsize=8,
                 frameon=False, ncol=3, bbox_to_anchor=(0.5, -0.06),
                 labelcolor=label_color)

    # --- Panel 6: Elevation / DEM (bottom-center) -------------------------
    ax_dem = fig.add_subplot(gs[2, 1])
    im_dem = ax_dem.imshow(dem, cmap="terrain", vmin=150, vmax=700, aspect="equal")
    _overlay_boundaries(ax_dem, summaries, "#333333")
    ax_dem.set_title("Elevation Model (ft)", fontsize=13,
                      fontweight="bold", color=title_color, pad=10)
    ax_dem.axis("off")
    cb3 = plt.colorbar(im_dem, ax=ax_dem, fraction=0.04, pad=0.01)
    cb3.set_label("Elevation (ft)", color=label_color, fontsize=10)
    cb3.ax.tick_params(colors=label_color, labelsize=8)

    # --- Panel 7: Summary stats (bottom-right) ----------------------------
    ax_txt = fig.add_subplot(gs[2, 2])
    ax_txt.set_facecolor("#1a1a2e")
    ax_txt.axis("off")

    natives = native_species(species)
    native_pct = sum(s.prevalence_pct for s in natives)

    stats_text = (
        "CITYWIDE SUMMARY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Total area assessed:   {:,.0f} acres\n"
        "Tree canopy:           {:,.0f} acres\n"
        "Canopy coverage:       {:.1f}%\n"
        "Neighborhoods:         {:d}\n"
        "Parks / greenspaces:   {:d}\n"
        "Species cataloged:     {:d}\n"
        "Native species:        {:.0f}%\n"
        "\n"
        "ECOSYSTEM SERVICES (annual)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Stormwater:      ${:>11,.0f}\n"
        "Air quality:     ${:>11,.0f}\n"
        "Carbon seq.:     ${:>11,.0f}\n"
        "Energy savings:  ${:>11,.0f}\n"
        "                 ───────────\n"
        "Total annual:    ${:>11,.0f}\n"
        "\n"
        "Property value:  ${:>11,.0f}\n"
    ).format(
        total_acres, canopy_acres, canopy_pct,
        len(neighborhoods), len(parks), len(species), native_pct,
        services.stormwater_value,
        services.air_quality_value,
        services.carbon_sequestration_value,
        services.energy_savings_value,
        services.total_annual,
        services.property_value_increase,
    )
    ax_txt.text(
        0.05, 0.95, stats_text,
        transform=ax_txt.transAxes,
        fontsize=10, fontfamily="monospace",
        color="#d0ffd0", verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#0d1b0d", edgecolor="#2d6a4f",
                  alpha=0.9),
    )

    return fig


def _overlay_boundaries(ax, summaries, color):
    """Draw neighbourhood outlines and labels on a raster panel."""
    for s in summaries:
        nid = s.neighborhood.neighborhood_id
        if nid not in NHOOD_BOXES:
            continue
        r0, r1, c0, c1 = NHOOD_BOXES[nid]
        rect = mpatches.FancyBboxPatch(
            (c0, r0), c1 - c0, r1 - r0,
            boxstyle="round,pad=1",
            linewidth=1.2, edgecolor=color, facecolor="none", alpha=0.6,
        )
        ax.add_patch(rect)
        cx = (c0 + c1) / 2
        cy = (r0 + r1) / 2
        ax.text(
            cx, cy,
            "{}\n{:.0f}%".format(s.neighborhood.name, s.canopy_pct),
            ha="center", va="center",
            fontsize=7, fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="black", alpha=0.55),
        )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "west_linn_canopy_dashboard.png"

    print("Generating canopy visualization dashboard...")
    fig = build_dashboard()
    fig.savefig(str(out_path), dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("Saved: {}".format(out_path))


if __name__ == "__main__":
    main()
