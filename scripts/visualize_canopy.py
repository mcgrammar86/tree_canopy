#!/usr/bin/env python3
"""
West Linn Tree Canopy Visualization
====================================
Generates a multi-panel figure simulating satellite imagery (NDVI) and
LiDAR-derived canopy height models using realistic polygon boundaries
that approximate West Linn's actual geography.

The city boundary follows the Willamette River (north/east), Tualatin
River (west/south), and I-205 corridor.  Neighborhood polygons are
hand-traced from West Linn's official neighborhood map.

Outputs:  output/west_linn_canopy_dashboard.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, FancyArrowPatch
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
DPI = 150
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# ---------------------------------------------------------------------------
# Geographic coordinate system
# ---------------------------------------------------------------------------
# We work in a local coordinate system where x ~ longitude, y ~ latitude.
# The domain spans roughly (0, 0) to (1, 1), with:
#   x=0 (west / I-205)  ->  x=1 (east / Wilderness Park)
#   y=0 (south / Tualatin River)  ->  y=1 (north / Willamette River)
#
# West Linn sits on a bluff between the confluence of the Willamette and
# Tualatin rivers.  The Willamette runs roughly NW-SE along the north and
# east edges; the Tualatin curves along the south and west.  I-205 cuts
# through the western side.  The city is roughly triangular / fan-shaped,
# wider in the north and tapering toward the south.

# Willamette River polyline (flows NW along top/right of city)
WILLAMETTE_RIVER = np.array([
    (-0.05, 0.88), (0.08, 0.95), (0.20, 0.99), (0.35, 1.02),
    (0.50, 1.01), (0.65, 0.97), (0.78, 0.92), (0.88, 0.85),
    (0.95, 0.78), (1.02, 0.68), (1.05, 0.55),
])

# Tualatin River polyline (flows along south/west)
TUALATIN_RIVER = np.array([
    (-0.05, 0.88), (-0.08, 0.75), (-0.06, 0.60), (-0.03, 0.45),
    (0.02, 0.30), (0.10, 0.18), (0.22, 0.08), (0.35, 0.02),
    (0.50, -0.02), (0.65, -0.03), (0.80, 0.00), (0.95, 0.05),
    (1.05, 0.12),
])

# I-205 corridor (roughly north-south through western third)
I205_LINE = np.array([
    (0.18, 1.02), (0.17, 0.90), (0.16, 0.78), (0.15, 0.65),
    (0.14, 0.50), (0.12, 0.35), (0.10, 0.18),
])

# ---------------------------------------------------------------------------
# Neighborhood polygons — hand-traced from West Linn's neighborhood map
# Vertices are in (x, y) local coords.  Polygons should be closed (first
# vertex = last vertex) but the code will close them automatically.
# ---------------------------------------------------------------------------
NHOOD_POLYS = {
    # Robinwood — NW, along Willamette River and I-205, largest neighborhood
    "N04": np.array([
        (0.00, 0.92), (0.08, 0.96), (0.18, 0.99), (0.30, 1.00),
        (0.30, 0.82), (0.18, 0.78), (0.16, 0.65), (0.14, 0.55),
        (0.00, 0.55), (-0.04, 0.65), (-0.05, 0.78), (0.00, 0.92),
    ]),
    # Willamette — NE, historic downtown along the river
    "N07": np.array([
        (0.30, 1.00), (0.48, 1.02), (0.62, 0.98), (0.75, 0.93),
        (0.80, 0.88), (0.72, 0.72), (0.55, 0.72), (0.42, 0.75),
        (0.30, 0.82), (0.30, 1.00),
    ]),
    # Bolton — west-central, between I-205 and city center
    "N01": np.array([
        (0.00, 0.55), (0.14, 0.55), (0.16, 0.65), (0.18, 0.78),
        (0.30, 0.82), (0.30, 0.72), (0.28, 0.60), (0.25, 0.48),
        (0.12, 0.38), (0.04, 0.35), (0.00, 0.40), (0.00, 0.55),
    ]),
    # Bland Circle — central
    "N10": np.array([
        (0.25, 0.48), (0.28, 0.60), (0.30, 0.72), (0.42, 0.75),
        (0.55, 0.72), (0.52, 0.58), (0.48, 0.48), (0.42, 0.42),
        (0.35, 0.40), (0.25, 0.48),
    ]),
    # Marylhurst — east-central, includes old college campus
    "N03": np.array([
        (0.55, 0.72), (0.72, 0.72), (0.80, 0.88), (0.88, 0.82),
        (0.92, 0.72), (0.88, 0.58), (0.78, 0.48), (0.65, 0.45),
        (0.52, 0.58), (0.55, 0.72),
    ]),
    # Sunset — southwest
    "N05": np.array([
        (0.04, 0.35), (0.12, 0.38), (0.25, 0.48), (0.35, 0.40),
        (0.32, 0.28), (0.25, 0.20), (0.18, 0.15), (0.10, 0.18),
        (0.04, 0.25), (0.04, 0.35),
    ]),
    # Savanna Oaks — south-central
    "N06": np.array([
        (0.35, 0.40), (0.42, 0.42), (0.48, 0.48), (0.52, 0.42),
        (0.50, 0.30), (0.45, 0.22), (0.38, 0.18), (0.32, 0.20),
        (0.32, 0.28), (0.35, 0.40),
    ]),
    # Tanner Basin — south-east
    "N08": np.array([
        (0.48, 0.48), (0.52, 0.58), (0.65, 0.45), (0.78, 0.48),
        (0.82, 0.38), (0.75, 0.28), (0.65, 0.22), (0.55, 0.22),
        (0.50, 0.30), (0.52, 0.42), (0.48, 0.48),
    ]),
    # Parker Crest — south, higher elevation
    "N09": np.array([
        (0.32, 0.20), (0.38, 0.18), (0.45, 0.22), (0.50, 0.30),
        (0.55, 0.22), (0.50, 0.10), (0.42, 0.05), (0.32, 0.05),
        (0.25, 0.10), (0.25, 0.20), (0.32, 0.20),
    ]),
    # Hidden Springs — far south/southeast, highest elevation
    "N02": np.array([
        (0.55, 0.22), (0.65, 0.22), (0.75, 0.28), (0.82, 0.22),
        (0.80, 0.10), (0.72, 0.04), (0.60, 0.02), (0.50, 0.05),
        (0.50, 0.10), (0.55, 0.22),
    ]),
}

# City outline — union of all neighborhoods (convex-ish hull)
CITY_OUTLINE = np.array([
    (-0.05, 0.78), (0.00, 0.92), (0.08, 0.96), (0.18, 0.99),
    (0.30, 1.00), (0.48, 1.02), (0.62, 0.98), (0.75, 0.93),
    (0.80, 0.88), (0.88, 0.82), (0.92, 0.72), (0.88, 0.58),
    (0.82, 0.38), (0.82, 0.22), (0.80, 0.10), (0.72, 0.04),
    (0.60, 0.02), (0.50, -0.02), (0.42, 0.05), (0.32, 0.05),
    (0.25, 0.10), (0.18, 0.15), (0.10, 0.18), (0.04, 0.25),
    (0.00, 0.40), (-0.04, 0.55), (-0.06, 0.65), (-0.05, 0.78),
])


# ---------------------------------------------------------------------------
# Raster generation helpers
# ---------------------------------------------------------------------------

def _smooth_noise(shape, scale=8, rng=None):
    """Generate smooth 2D noise by upsampling a small random grid."""
    rows, cols = shape
    if rng is None:
        rng = np.random.default_rng(SEED)
    sr = max(rows // scale, 2)
    sc = max(cols // scale, 2)
    lo = rng.random((sr, sc)).astype(np.float32)
    ri = np.linspace(0, sr - 1, rows)
    ci = np.linspace(0, sc - 1, cols)
    tmp = np.zeros((rows, sc), np.float32)
    for c in range(sc):
        tmp[:, c] = np.interp(ri, np.arange(sr), lo[:, c])
    out = np.zeros((rows, cols), np.float32)
    for r in range(rows):
        out[r, :] = np.interp(ci, np.arange(sc), tmp[r, :])
    return out


def _poly_mask(poly, xmin, xmax, ymin, ymax, nx, ny):
    """Return a boolean (ny, nx) mask for pixels inside polygon."""
    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymax, ymin, ny)  # y-axis flipped for image coords
    xx, yy = np.meshgrid(xs, ys)
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    verts = poly if np.allclose(poly[0], poly[-1]) else np.vstack([poly, poly[0:1]])
    path = MplPath(verts)
    mask = path.contains_points(pts).reshape(ny, nx)
    return mask


def _city_mask(nx, ny, xmin=-0.1, xmax=1.0, ymin=-0.05, ymax=1.05):
    return _poly_mask(CITY_OUTLINE, xmin, xmax, ymin, ymax, nx, ny)


def _build_summary_map(summaries):
    """Map neighborhood_id -> summary."""
    return {s.neighborhood.neighborhood_id: s for s in summaries}


def _generate_ndvi_raster(summaries, nx, ny, rng,
                          xmin=-0.1, xmax=1.0, ymin=-0.05, ymax=1.05):
    """Generate NDVI raster with values driven by neighborhood canopy %."""
    smap = _build_summary_map(summaries)
    # base noise
    ndvi = _smooth_noise((ny, nx), scale=12, rng=rng) * 0.12 + 0.15
    # water band at top (low NDVI)
    water_y = int(ny * 0.04)
    ndvi[:water_y, :] = rng.uniform(0.02, 0.08, (water_y, nx))

    for nid, poly in NHOOD_POLYS.items():
        if nid not in smap:
            continue
        s = smap[nid]
        mask = _poly_mask(poly, xmin, xmax, ymin, ymax, nx, ny)
        canopy_f = s.canopy_pct / 100.0
        imp_f = s.total_impervious_acres / max(s.neighborhood.area_acres, 1)

        # base value proportional to canopy
        base_val = canopy_f * 0.80 + 0.10
        patch = rng.normal(loc=base_val, scale=0.08, size=(ny, nx)).astype(np.float32)

        # add park hotspots
        for park in s.parks:
            cx_p = np.mean(poly[:, 0]) + rng.uniform(-0.05, 0.05)
            cy_p = np.mean(poly[:, 1]) + rng.uniform(-0.05, 0.05)
            px = int((cx_p - xmin) / (xmax - xmin) * nx)
            py = int((1 - (cy_p - ymin) / (ymax - ymin)) * ny)
            rad = int(np.sqrt(park.area_acres) * 2.5) + 3
            yy, xx = np.ogrid[max(py-rad,0):min(py+rad,ny),
                               max(px-rad,0):min(px+rad,nx)]
            dist2 = (yy - py)**2 + (xx - px)**2
            park_boost = 0.15 * np.exp(-dist2 / (2 * rad**2))
            sl_y = slice(max(py-rad,0), min(py+rad,ny))
            sl_x = slice(max(px-rad,0), min(px+rad,nx))
            patch[sl_y, sl_x] += park_boost

        # impervious spots (reduced NDVI)
        imp_mask = rng.random((ny, nx)) < imp_f * 0.5
        patch[imp_mask] -= 0.20

        ndvi[mask] = patch[mask]

    # mask outside city
    city = _city_mask(nx, ny, xmin, xmax, ymin, ymax)
    ndvi[~city] = np.nan
    return np.clip(ndvi, 0, 1)


def _generate_chm_raster(summaries, nx, ny, rng,
                         xmin=-0.1, xmax=1.0, ymin=-0.05, ymax=1.05):
    """Generate canopy height model with individual tree blobs."""
    smap = _build_summary_map(summaries)
    chm = np.zeros((ny, nx), np.float32)

    for nid, poly in NHOOD_POLYS.items():
        if nid not in smap:
            continue
        s = smap[nid]
        mask = _poly_mask(poly, xmin, xmax, ymin, ymax, nx, ny)
        canopy_f = s.canopy_pct / 100.0

        n_trees = int(canopy_f * np.sum(mask) * 0.06)
        # find pixel locations inside polygon
        ys_in, xs_in = np.where(mask)
        if len(ys_in) == 0:
            continue
        for _ in range(n_trees):
            idx = rng.integers(0, len(ys_in))
            ty, tx = ys_in[idx], xs_in[idx]
            h = rng.normal(loc=60 * canopy_f + 35, scale=22)
            h = np.clip(h, 12, 150)
            sp = rng.integers(2, 5)
            y0 = max(ty - sp, 0)
            y1 = min(ty + sp + 1, ny)
            x0 = max(tx - sp, 0)
            x1 = min(tx + sp + 1, nx)
            yr = np.arange(y0, y1)[:, None]
            xr = np.arange(x0, x1)[None, :]
            gauss = h * np.exp(-((yr - ty)**2 + (xr - tx)**2) / (2 * sp))
            chm[y0:y1, x0:x1] = np.maximum(chm[y0:y1, x0:x1], gauss)

        # extra tall trees in parks
        for park in s.parks:
            cx_p = np.mean(poly[:, 0]) + rng.uniform(-0.04, 0.04)
            cy_p = np.mean(poly[:, 1]) + rng.uniform(-0.04, 0.04)
            px = int((cx_p - xmin) / (xmax - xmin) * nx)
            py = int((1 - (cy_p - ymin) / (ymax - ymin)) * ny)
            for _ in range(int(park.canopy_acres * 0.4)):
                tx = int(np.clip(rng.normal(px, 8), 0, nx - 1))
                ty = int(np.clip(rng.normal(py, 8), 0, ny - 1))
                h = rng.normal(loc=100, scale=18)
                h = np.clip(h, 50, 150)
                sp = rng.integers(2, 5)
                y0 = max(ty - sp, 0)
                y1 = min(ty + sp + 1, ny)
                x0 = max(tx - sp, 0)
                x1 = min(tx + sp + 1, nx)
                yr = np.arange(y0, y1)[:, None]
                xr = np.arange(x0, x1)[None, :]
                gauss = h * np.exp(-((yr - ty)**2 + (xr - tx)**2) / (2 * sp))
                chm[y0:y1, x0:x1] = np.maximum(chm[y0:y1, x0:x1], gauss)

    city = _city_mask(nx, ny, xmin, xmax, ymin, ymax)
    chm[~city] = np.nan
    return chm


def _generate_dem_raster(neighborhoods, nx, ny, rng,
                         xmin=-0.1, xmax=1.0, ymin=-0.05, ymax=1.05):
    """Generate elevation surface from neighborhood average elevations."""
    nmap = {n.neighborhood_id: n for n in neighborhoods}
    dem = _smooth_noise((ny, nx), scale=15, rng=rng) * 30 + 200

    for nid, poly in NHOOD_POLYS.items():
        if nid not in nmap:
            continue
        mask = _poly_mask(poly, xmin, xmax, ymin, ymax, nx, ny)
        elev = nmap[nid].elevation_ft_avg
        patch = rng.normal(loc=elev, scale=25, size=(ny, nx)).astype(np.float32)
        dem[mask] = dem[mask] * 0.15 + patch[mask] * 0.85

    city = _city_mask(nx, ny, xmin, xmax, ymin, ymax)
    dem[~city] = np.nan
    return dem


# ---------------------------------------------------------------------------
# Colormaps
# ---------------------------------------------------------------------------

def _ndvi_cmap():
    colors = [
        (0.60, 0.50, 0.35),  # bare soil
        (0.80, 0.78, 0.55),  # dry grass
        (0.55, 0.75, 0.30),  # light veg
        (0.20, 0.58, 0.15),  # moderate
        (0.05, 0.40, 0.05),  # dense
        (0.00, 0.25, 0.00),  # very dense
    ]
    cmap = LinearSegmentedColormap.from_list("ndvi", colors, N=256)
    cmap.set_bad("#1a1a2e")
    return cmap


def _chm_cmap():
    colors = [
        (0.88, 0.86, 0.80),  # ground
        (0.72, 0.82, 0.42),  # shrub
        (0.38, 0.70, 0.22),  # small tree
        (0.15, 0.52, 0.12),  # medium
        (0.05, 0.38, 0.08),  # tall
        (0.02, 0.22, 0.02),  # old growth
    ]
    cmap = LinearSegmentedColormap.from_list("chm", colors, N=256)
    cmap.set_bad("#1a1a2e")
    return cmap


def _dem_cmap():
    colors = [
        (0.30, 0.55, 0.30),  # low river valleys
        (0.50, 0.70, 0.35),  # low hills
        (0.70, 0.78, 0.45),  # mid elevation
        (0.85, 0.82, 0.55),  # upper slopes
        (0.75, 0.65, 0.45),  # high ridges
        (0.60, 0.50, 0.35),  # peaks
    ]
    cmap = LinearSegmentedColormap.from_list("dem", colors, N=256)
    cmap.set_bad("#1a1a2e")
    return cmap


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_river(ax, pts, width=3.5, color="#3a7bbf", alpha=0.85):
    """Draw a smooth river polyline."""
    from matplotlib.lines import Line2D
    ax.plot(pts[:, 0], pts[:, 1], color=color, linewidth=width,
            alpha=alpha, solid_capstyle="round", zorder=5)
    # water fill above the river
    ax.fill_between(pts[:, 0], pts[:, 1], y2=1.1,
                    color=color, alpha=0.25, zorder=1)


def _draw_i205(ax, pts, color="#aaaaaa", alpha=0.6):
    ax.plot(pts[:, 0], pts[:, 1], color=color, linewidth=2,
            linestyle="--", alpha=alpha, zorder=6)
    mid = len(pts) // 2
    ax.text(pts[mid, 0] - 0.03, pts[mid, 1], "I-205",
            fontsize=7, color=color, alpha=0.8, rotation=85,
            ha="center", va="center", fontweight="bold", zorder=7)


def _draw_neighborhood_boundaries(ax, summaries, label_fontsize=7,
                                   edge_color="white", edge_alpha=0.7):
    """Draw neighborhood polygon outlines and labels."""
    smap = _build_summary_map(summaries)
    for nid, poly in NHOOD_POLYS.items():
        verts = poly if np.allclose(poly[0], poly[-1]) else np.vstack([poly, poly[0:1]])
        codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(verts) - 2) + [MplPath.CLOSEPOLY]
        path = MplPath(verts, codes)
        patch = PathPatch(path, facecolor="none", edgecolor=edge_color,
                          linewidth=1.0, alpha=edge_alpha, zorder=8)
        ax.add_patch(patch)

        cx = np.mean(poly[:, 0])
        cy = np.mean(poly[:, 1])
        if nid in smap:
            s = smap[nid]
            label = "{}\n{:.0f}%".format(s.neighborhood.name, s.canopy_pct)
        else:
            label = nid
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=label_fontsize, fontweight="bold", color="white",
                zorder=10,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="black",
                          alpha=0.55, edgecolor="none"))


def _style_map_ax(ax, title, title_color="#e0e0e0"):
    """Common styling for map axes."""
    ax.set_xlim(-0.12, 1.05)
    ax.set_ylim(-0.08, 1.08)
    ax.set_aspect("equal")
    ax.set_facecolor("#1a1a2e")
    ax.set_title(title, fontsize=14, fontweight="bold",
                 color=title_color, pad=10)
    ax.axis("off")


# ---------------------------------------------------------------------------
# Main dashboard
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
    NX, NY = 500, 500
    xmin, xmax, ymin, ymax = -0.1, 1.0, -0.05, 1.05
    extent = [xmin, xmax, ymin, ymax]

    # generate rasters
    ndvi = _generate_ndvi_raster(summaries, NX, NY, rng, xmin, xmax, ymin, ymax)
    rng2 = np.random.default_rng(SEED + 1)
    chm = _generate_chm_raster(summaries, NX, NY, rng2, xmin, xmax, ymin, ymax)
    rng3 = np.random.default_rng(SEED + 2)
    dem = _generate_dem_raster(neighborhoods, NX, NY, rng3, xmin, xmax, ymin, ymax)

    # ---- Figure layout: 2x2 grid ------------------------------------------
    #   top-left:     NDVI map
    #   top-right:    LiDAR CHM
    #   bottom-left:  Elevation + bar chart inset
    #   bottom-right: Stats + ecosystem services
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(22, 20), facecolor="#1a1a2e")
    gs = gridspec.GridSpec(2, 2, hspace=0.22, wspace=0.18,
                           left=0.04, right=0.96, top=0.92, bottom=0.04)

    tc = "#e0e0e0"
    lc = "#c0c0c0"

    fig.suptitle(
        "WEST LINN, OREGON  —  TREE CANOPY INVENTORY\n"
        "Satellite NDVI  &  LiDAR Canopy Height Analysis",
        fontsize=22, fontweight="bold", color=tc, y=0.97,
    )

    # --- Panel 1: NDVI -----------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    im1 = ax1.imshow(ndvi, cmap=_ndvi_cmap(), vmin=0, vmax=0.85,
                     extent=extent, origin="upper", aspect="equal",
                     interpolation="bilinear")
    _draw_river(ax1, WILLAMETTE_RIVER, width=6, color="#2a6faa")
    _draw_river(ax1, TUALATIN_RIVER, width=4, color="#3580bb")
    _draw_i205(ax1, I205_LINE)
    _draw_neighborhood_boundaries(ax1, summaries, label_fontsize=7)
    _style_map_ax(ax1, "Satellite NDVI  (Normalized Difference Vegetation Index)")
    cb1 = plt.colorbar(im1, ax=ax1, fraction=0.035, pad=0.02, shrink=0.85)
    cb1.set_label("NDVI", color=lc, fontsize=10)
    cb1.ax.tick_params(colors=lc, labelsize=8)

    # compass rose
    ax1.annotate("N", xy=(0.95, 1.02), fontsize=11, fontweight="bold",
                 color=tc, ha="center", va="bottom")
    ax1.annotate("", xy=(0.95, 1.02), xytext=(0.95, 0.92),
                 arrowprops=dict(arrowstyle="->", color=tc, lw=1.5))

    # river labels
    ax1.text(0.55, 1.04, "Willamette River", fontsize=8, color="#5ba3d9",
             fontstyle="italic", ha="center", zorder=11)
    ax1.text(-0.08, 0.50, "Tualatin\nRiver", fontsize=7, color="#5ba3d9",
             fontstyle="italic", ha="center", rotation=60, zorder=11)

    # --- Panel 2: LiDAR CHM -----------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    im2 = ax2.imshow(chm, cmap=_chm_cmap(), vmin=0, vmax=140,
                     extent=extent, origin="upper", aspect="equal",
                     interpolation="bilinear")
    _draw_river(ax2, WILLAMETTE_RIVER, width=6, color="#2a6faa")
    _draw_river(ax2, TUALATIN_RIVER, width=4, color="#3580bb")
    _draw_i205(ax2, I205_LINE)
    _draw_neighborhood_boundaries(ax2, summaries, label_fontsize=7)
    _style_map_ax(ax2, "LiDAR Canopy Height Model  (CHM)")
    cb2 = plt.colorbar(im2, ax=ax2, fraction=0.035, pad=0.02, shrink=0.85)
    cb2.set_label("Canopy Height (ft)", color=lc, fontsize=10)
    cb2.ax.tick_params(colors=lc, labelsize=8)

    # height class legend
    ht_labels = [("0-20 ft", "#e0dcc8"), ("20-50 ft", "#b8d26b"),
                 ("50-80 ft", "#5fb338"), ("80-110 ft", "#27851e"),
                 ("110-140 ft", "#0a6114"), (">140 ft", "#053808")]
    ht_patches = [mpatches.Patch(color=c, label=l) for l, c in ht_labels]
    ax2.legend(handles=ht_patches, loc="lower left", fontsize=7,
               frameon=True, facecolor="#1a1a2e", edgecolor="#444",
               labelcolor=lc, ncol=2, bbox_to_anchor=(0.0, -0.01))

    # --- Panel 3: Elevation + bar chart -----------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    im3 = ax3.imshow(dem, cmap=_dem_cmap(), vmin=150, vmax=680,
                     extent=extent, origin="upper", aspect="equal",
                     interpolation="bilinear")
    _draw_river(ax3, WILLAMETTE_RIVER, width=6, color="#2a6faa")
    _draw_river(ax3, TUALATIN_RIVER, width=4, color="#3580bb")
    _draw_i205(ax3, I205_LINE)
    _draw_neighborhood_boundaries(ax3, summaries, label_fontsize=6,
                                   edge_color="#333333")
    _style_map_ax(ax3, "Digital Elevation Model  (ft above sea level)")
    cb3 = plt.colorbar(im3, ax=ax3, fraction=0.035, pad=0.02, shrink=0.85)
    cb3.set_label("Elevation (ft)", color=lc, fontsize=10)
    cb3.ax.tick_params(colors=lc, labelsize=8)

    # inset bar chart for canopy by neighborhood
    ax_bar = fig.add_axes([0.30, 0.06, 0.18, 0.22])
    ax_bar.set_facecolor("#0d1b0d")
    ax_bar.patch.set_alpha(0.85)
    sorted_s = sorted(summaries, key=lambda s: s.canopy_pct)
    names = [s.neighborhood.name[:12] for s in sorted_s]
    pcts = [s.canopy_pct for s in sorted_s]
    y_pos = np.arange(len(names))
    bar_colors = [plt.cm.YlGn(p / 65.0) for p in pcts]
    ax_bar.barh(y_pos, pcts, color=bar_colors, edgecolor="#333", linewidth=0.4, height=0.7)
    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels(names)
    ax_bar.axvline(x=canopy_pct, color="#ff6b6b", linestyle="--", linewidth=1, alpha=0.7)
    ax_bar.set_xlim(0, 68)
    ax_bar.tick_params(colors=lc, labelsize=5.5)
    ax_bar.set_title("Canopy %", fontsize=7, color=tc, pad=3)
    for spine in ax_bar.spines.values():
        spine.set_color("#444")
    for i, p in enumerate(pcts):
        ax_bar.text(p + 0.8, i, "{:.0f}%".format(p), va="center",
                    fontsize=5, color=lc)

    # --- Panel 4: Stats & ecosystem services ------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor("#1a1a2e")
    ax4.axis("off")

    natives = native_species(species)
    native_pct = sum(s.prevalence_pct for s in natives)

    # Summary box
    summary = (
        "CITYWIDE SUMMARY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  Total area assessed:    {:>7,.0f} acres\n"
        "  Tree canopy cover:      {:>7,.0f} acres\n"
        "  Canopy coverage:        {:>7.1f}%\n"
        "  Neighborhoods:          {:>7d}\n"
        "  Parks & greenspaces:    {:>7d}\n"
        "  Species cataloged:      {:>7d}\n"
        "  Native species share:   {:>7.0f}%\n"
    ).format(total_acres, canopy_acres, canopy_pct,
             len(neighborhoods), len(parks), len(species), native_pct)

    eco = (
        "\n\nECOSYSTEM SERVICES  (estimated annual value)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  Stormwater management:  ${:>12,.0f}\n"
        "  Air quality improvement:${:>12,.0f}\n"
        "  Carbon sequestration:   ${:>12,.0f}\n"
        "  Energy savings:         ${:>12,.0f}\n"
        "                          ─────────────\n"
        "  Total annual value:     ${:>12,.0f}\n\n"
        "  Property value uplift:  ${:>12,.0f}\n"
    ).format(
        services.stormwater_value, services.air_quality_value,
        services.carbon_sequestration_value, services.energy_savings_value,
        services.total_annual, services.property_value_increase,
    )

    ax4.text(0.05, 0.95, summary + eco,
             transform=ax4.transAxes, fontsize=12, fontfamily="monospace",
             color="#c0f0c0", va="top",
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#0a150a",
                       edgecolor="#2d6a4f", alpha=0.95, linewidth=1.5))

    # Land-use pie chart as inset
    ax_pie = ax4.inset_axes([0.10, 0.02, 0.45, 0.32])
    ax_pie.set_facecolor("#0a150a")
    lu = canopy_by_land_use(records)
    lu_items = sorted(lu.items(), key=lambda kv: kv[1]["canopy"], reverse=True)
    lu_names = [k for k, _ in lu_items]
    lu_vals = [v["canopy"] for _, v in lu_items]
    pie_c = ["#1b4332", "#2d6a4f", "#40916c", "#52b788",
             "#74c69d", "#95d5b2", "#b7e4c7"]
    wedges, _, autotexts = ax_pie.pie(
        lu_vals, labels=None, autopct="%1.0f%%",
        colors=pie_c[:len(lu_vals)], pctdistance=0.75, startangle=140,
        textprops={"fontsize": 7, "color": "#dddddd"})
    ax_pie.set_title("Canopy by Land Use", fontsize=9, color=tc, pad=4)
    ax_pie.legend(wedges, lu_names, loc="center left",
                  bbox_to_anchor=(1.0, 0.5), fontsize=6.5,
                  frameon=False, labelcolor=lc)

    # Data source note
    fig.text(0.50, 0.012,
             "Data: City of West Linn GIS  |  Oregon Dept. of Forestry  |  "
             "USDA i-Tree Eco  |  NLCD  |  Metro RLIS    "
             "Visualization: simulated NDVI & LiDAR from inventory data",
             ha="center", fontsize=8, color="#666666", fontstyle="italic")

    return fig


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
