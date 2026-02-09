#!/usr/bin/env python3
import argparse
import math
import ezdxf
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import split

# ----------------------------
# DXF IO helpers
# ----------------------------

def read_first_closed_lwpolyline_as_polygon(dxf_path):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # choose the largest closed LWPOLYLINE by bbox area
    best = None
    best_score = -1.0

    for e in msp:
        if e.dxftype() != "LWPOLYLINE":
            continue
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        if len(pts) < 3:
            continue
        if pts[0] != pts[-1]:
            # allow "closed flag" OR explicit closure
            if not bool(getattr(e, "closed", False)):
                continue
            pts = pts + [pts[0]]

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        score = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if score > best_score:
            best_score = score
            best = pts

    if best is None:
        raise RuntimeError("No closed LWPOLYLINE found. Ensure your outline is a single closed polyline in DXF.")

    poly = Polygon(best)
    if (not poly.is_valid) or poly.area <= 0:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise RuntimeError("Outline polygon invalid/empty after cleanup. Check DXF.")

    return poly


def write_polygon_and_holes_to_dxf(out_path, poly: Polygon, holes, layer_outline="CUT", layer_holes="PINS"):
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # outline
    coords = list(poly.exterior.coords)
    msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": layer_outline})

    # holes (circles)
    for (cx, cy, r) in holes:
        msp.add_circle((cx, cy), r, dxfattribs={"layer": layer_holes})

    doc.saveas(out_path)


# ----------------------------
# Geometry helpers: half-plane clipping for flats
# ----------------------------

def normalize(v):
    n = math.hypot(v[0], v[1])
    if n < 1e-12:
        return (0.0, 0.0)
    return (v[0]/n, v[1]/n)


def half_plane_polygon(p0, n_out, keep_inside=True, extent=5000.0):
    """
    Build a huge polygon representing one half-plane.
    Line is defined by point p0 and outward normal n_out.
    keep_inside=True keeps points where (x-p0)·n_out <= 0
    """
    nx, ny = normalize(n_out)
    # tangent direction
    tx, ty = -ny, nx

    # pick a far point along normal to include large region
    # We construct a big quad that covers the desired half-plane.
    # Two points on the line
    a = (p0[0] + tx*extent, p0[1] + ty*extent)
    b = (p0[0] - tx*extent, p0[1] - ty*extent)

    # push outward/ inward
    if keep_inside:
        # keep side opposite to n_out => move polygon far in -n direction
        c = (b[0] - nx*extent, b[1] - ny*extent)
        d = (a[0] - nx*extent, a[1] - ny*extent)
    else:
        c = (b[0] + nx*extent, b[1] + ny*extent)
        d = (a[0] + nx*extent, a[1] + ny*extent)

    return Polygon([a, b, c, d])


def clip_with_flat(poly: Polygon, p0, n_out):
    hp = half_plane_polygon(p0, n_out, keep_inside=True, extent=10000.0)
    out = poly.intersection(hp)
    if out.is_empty:
        raise RuntimeError("Flat clipping produced empty geometry. Check parameters.")
    # if multiple, keep largest
    if out.geom_type == "MultiPolygon":
        out = max(out.geoms, key=lambda g: g.area)
    return out


# ----------------------------
# Corner detection (robust enough for your current outlines)
# ----------------------------

def sample_exterior(poly: Polygon, n=2000):
    ring = LineString(poly.exterior.coords)
    L = ring.length
    ts = np.linspace(0, L, n, endpoint=False)
    pts = [ring.interpolate(t).coords[0] for t in ts]
    return np.array(pts, dtype=float)


def curvature_peaks(points, k=5):
    """
    Rough curvature proxy: angle change between segments.
    Returns indices sorted by descending "cornerness".
    """
    pts = points
    N = len(pts)
    score = np.zeros(N)

    for i in range(N):
        p0 = pts[(i-3) % N]
        p1 = pts[i]
        p2 = pts[(i+3) % N]
        v1 = p0 - p1
        v2 = p2 - p1
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        v1 /= n1
        v2 /= n2
        # angle between v1 and v2 (0..pi)
        ang = math.acos(max(-1.0, min(1.0, float(np.dot(v1, v2)))))
        score[i] = ang

    idx = np.argsort(-score)
    return idx, score


def pick_four_corners(poly: Polygon, axis_is_x=True):
    """
    Find 4 corner-ish points around the waist:
    - two with y>0 (upper edge), two with y<0 (lower edge)
    - split by x (near neck / near end) in each sign
    """
    pts = sample_exterior(poly, n=2500)

    # Determine center and longitudinal axis
    minx, miny, maxx, maxy = poly.bounds
    cx = 0.5*(minx+maxx)
    cy = 0.5*(miny+maxy)
    mid_long = cx if axis_is_x else cy

    idx, score = curvature_peaks(pts)

    # consider only points around waist band (middle 50% of length axis)
    # cello corners live near the waist, not at extreme ends
    if axis_is_x:
        long = pts[:,0]
        lo = minx + 0.25*(maxx-minx)
        hi = minx + 0.75*(maxx-minx)
        band = (long >= lo) & (long <= hi)
        side = pts[:,1]
        longcoord = pts[:,0]
    else:
        long = pts[:,1]
        lo = miny + 0.25*(maxy-miny)
        hi = miny + 0.75*(maxy-miny)
        band = (long >= lo) & (long <= hi)
        side = pts[:,0]
        longcoord = pts[:,1]

    # choose candidates
    cand = [i for i in idx[:400] if band[i]]
    if len(cand) < 20:
        cand = list(idx[:400])

    # pick two on upper side and two on lower side
    upper = [i for i in cand if side[i] >= 0]
    lower = [i for i in cand if side[i] < 0]

    def pick_two_by_long(inds):
        # split into near neck vs near end by comparing to midpoint
        a = [i for i in inds if longcoord[i] >= mid_long]
        b = [i for i in inds if longcoord[i] < mid_long]
        # pick best from each bucket
        if not a or not b:
            # fallback: pick top2 overall spaced
            top = inds[:2]
            return top
        return [a[0], b[0]]

    u2 = pick_two_by_long(upper)
    l2 = pick_two_by_long(lower)

    corners = [pts[i] for i in (u2 + l2)]
    return corners, (cx, cy)


# ----------------------------
# Pins + splitting
# ----------------------------

def default_pins(poly: Polygon, axis_is_x=True, x_center=None, pin_diam=6.0):
    """
    Places 3 pins along centerline inside the mold.
    """
    minx, miny, maxx, maxy = poly.bounds
    cx = 0.5*(minx+maxx)
    cy = 0.5*(miny+maxy)
    if x_center is None:
        x_center = cx if axis_is_x else cy

    r = 0.5*pin_diam

    holes = []
    if axis_is_x:
        # centerline y = cy
        xs = [minx + 0.25*(maxx-minx), minx + 0.50*(maxx-minx), minx + 0.75*(maxx-minx)]
        for x in xs:
            p = Point(x, cy)
            if poly.contains(p.buffer(r*1.2)):
                holes.append((x, cy, r))
    else:
        ys = [miny + 0.25*(maxy-miny), miny + 0.50*(maxy-miny), miny + 0.75*(maxy-miny)]
        for y in ys:
            p = Point(cx, y)
            if poly.contains(p.buffer(r*1.2)):
                holes.append((cx, y, r))

    return holes


def split_halves(poly: Polygon, axis_is_x=True):
    minx, miny, maxx, maxy = poly.bounds
    cx = 0.5*(minx+maxx)
    cy = 0.5*(miny+maxy)

    if axis_is_x:
        # split by horizontal centerline y=cy -> top/bottom halves
        # But for inner mold, we usually want left/right halves split by centerline along length.
        # With length along X, centerline is Y=cy, split should be along that (i.e. line parallel to X).
        splitter = LineString([(minx-1000, cy), (maxx+1000, cy)])
    else:
        splitter = LineString([(cx, miny-1000), (cx, maxy+1000)])

    parts = split(poly, splitter)
    if len(parts.geoms) < 2:
        raise RuntimeError("Split did not produce two halves. Check axis orientation.")
    # return two largest
    geoms = sorted(parts.geoms, key=lambda g: g.area, reverse=True)[:2]
    return geoms[0], geoms[1]


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Generate cello inner mold: block flats + pin holes + halves")
    ap.add_argument("input_outline_dxf", help="DXF containing ONE closed LWPOLYLINE = inner mold outline (already offset)")
    ap.add_argument("--out-prefix", default="mold", help="output prefix (creates prefix_full.dxf, prefix_halfA.dxf, prefix_halfB.dxf)")
    ap.add_argument("--axis", choices=["x","y"], default="x", help="longitudinal axis of body in your DXF (usually x)")
    ap.add_argument("--neck-flat-mm", type=float, default=62.0, help="neck block flat depth (mm cut off from extreme end)")
    ap.add_argument("--end-flat-mm", type=float, default=58.0, help="end block flat depth (mm cut off from extreme end)")
    ap.add_argument("--corner-flat-mm", type=float, default=34.0, help="corner block flat depth (mm)")
    ap.add_argument("--corner-angle-deg", type=float, default=45.0, help="corner flat normal angle relative to axis")
    ap.add_argument("--pin-diam-mm", type=float, default=6.0, help="alignment pin hole diameter")
    args = ap.parse_args()

    axis_is_x = (args.axis == "x")
    poly = read_first_closed_lwpolyline_as_polygon(args.input_outline_dxf)

    minx, miny, maxx, maxy = poly.bounds
    cx = 0.5*(minx+maxx)
    cy = 0.5*(miny+maxy)
    print(f"Loaded outline bounds dx={maxx-minx:.2f} dy={maxy-miny:.2f} center=({cx:.2f},{cy:.2f})")

    # --- Neck & End flats (cut planes perpendicular to longitudinal axis) ---
    if axis_is_x:
        # neck at +X, end at -X
        x_neck = maxx - args.neck_flat_mm
        x_end  = minx + args.end_flat_mm
        poly = clip_with_flat(poly, (x_neck, cy), n_out=(+1, 0))  # remove +X cap
        poly = clip_with_flat(poly, (x_end,  cy), n_out=(-1, 0))  # remove -X cap
    else:
        y_neck = maxy - args.neck_flat_mm
        y_end  = miny + args.end_flat_mm
        poly = clip_with_flat(poly, (cx, y_neck), n_out=(0, +1))
        poly = clip_with_flat(poly, (cx, y_end ), n_out=(0, -1))

    # --- Corner flats (auto-detect corners near waist, clip with diagonal planes) ---
    corners, (ccx, ccy) = pick_four_corners(poly, axis_is_x=axis_is_x)

    ang = math.radians(args.corner_angle_deg)
    # normal base in (+axis, +side)
    base = (math.cos(ang), math.sin(ang)) if axis_is_x else (math.sin(ang), math.cos(ang))

    for (px, py) in corners:
        # Determine signs by which quadrant relative to center
        sx = +1 if (px - ccx) >= 0 else -1
        sy = +1 if (py - ccy) >= 0 else -1

        if axis_is_x:
            n_out = (sx*base[0], sy*base[1])   # diagonal outward
        else:
            # if length along Y, swap role
            n_out = (sy*base[1], sx*base[0])

        # place cut line slightly inward from the corner point
        nx, ny = normalize(n_out)
        p0 = (px - nx*args.corner_flat_mm, py - ny*args.corner_flat_mm)
        poly = clip_with_flat(poly, p0, n_out=n_out)

    # --- Pins ---
    holes = default_pins(poly, axis_is_x=axis_is_x, pin_diam=args.pin_diam_mm)

    # --- Full export ---
    full_path = f"{args.out_prefix}_full.dxf"
    write_polygon_and_holes_to_dxf(full_path, poly, holes)
    print("Wrote:", full_path)

    # --- Split halves (along centerline) ---
    halfA, halfB = split_halves(poly, axis_is_x=axis_is_x)
    write_polygon_and_holes_to_dxf(f"{args.out_prefix}_halfA.dxf", halfA, holes)
    write_polygon_and_holes_to_dxf(f"{args.out_prefix}_halfB.dxf", halfB, holes)
    print("Wrote:", f"{args.out_prefix}_halfA.dxf", f"{args.out_prefix}_halfB.dxf")


if __name__ == "__main__":
    main()

