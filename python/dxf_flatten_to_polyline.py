#!/usr/bin/env python3
import argparse
import math
import ezdxf


def sample_arc(cx, cy, r, a0_deg, a1_deg, tol):
    a0 = math.radians(a0_deg)
    a1 = math.radians(a1_deg)
    if a1 < a0:
        a1 += 2.0 * math.pi

    tol = max(tol, 1e-6)
    if r <= tol:
        n = 128
    else:
        # sagitta-based step
        dmax = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tol / r)))
        n = max(64, int(math.ceil((a1 - a0) / max(dmax, 1e-3))))

    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * (i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def try_make_path_points(e, tol):
    """
    Best-effort: use ezdxf.path.make_path flattening (works great for SPLINE/ELLIPSE/ARC).
    Falls back silently if ezdxf.path is unavailable in your version.
    """
    try:
        from ezdxf.path import make_path
        p = make_path(e)
        pts = [(v.x, v.y) for v in p.flattening(distance=tol)]
        return pts if len(pts) >= 2 else []
    except Exception:
        return []


def flatten_entity_to_points(e, tol):
    t = e.dxftype()

    # Prefer make_path flattening if it works
    pts = try_make_path_points(e, tol)
    if pts:
        return pts

    if t == "LINE":
        s = e.dxf.start
        d = e.dxf.end
        return [(s.x, s.y), (d.x, d.y)]

    if t == "ARC":
        c = e.dxf.center
        r = float(e.dxf.radius)
        return sample_arc(c.x, c.y, r, float(e.dxf.start_angle), float(e.dxf.end_angle), tol)

    if t == "CIRCLE":
        c = e.dxf.center
        r = float(e.dxf.radius)
        return sample_arc(c.x, c.y, r, 0.0, 360.0, tol)

    if t in ("LWPOLYLINE", "POLYLINE"):
        out = []
        # Expand bulges to LINE/ARC where possible
        try:
            for ve in e.virtual_entities():
                out += flatten_entity_to_points(ve, tol)
            return out
        except Exception:
            # fallback: raw vertices (no bulge handling)
            try:
                if t == "LWPOLYLINE":
                    return [(p[0], p[1]) for p in e.get_points("xy")]
            except Exception:
                pass
            return []

    if t in ("SPLINE", "ELLIPSE"):
        # Try entity.flattening (some ezdxf builds support it)
        try:
            pts = [(p.x, p.y) for p in e.flattening(distance=tol)]
            return pts if len(pts) >= 2 else []
        except Exception:
            return []

    return []


def dedupe_consecutive(pts):
    if not pts:
        return pts
    clean = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1]) > 1e-10:
            clean.append(p)
    return clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dxf")
    ap.add_argument("output_dxf")
    ap.add_argument("--tol-mm", type=float, default=0.2, help="flatten tolerance in mm (smaller=more points)")
    args = ap.parse_args()

    doc = ezdxf.readfile(args.input_dxf)
    msp = doc.modelspace()

    outlines = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT", "DIMENSION", "HATCH"):
            continue
        pts = flatten_entity_to_points(e, args.tol_mm)
        pts = dedupe_consecutive(pts)
        if len(pts) >= 2:
            outlines.append(pts)

    if not outlines:
        raise RuntimeError("No entities flattened. DXF may contain unsupported entities or be empty.")

    out = ezdxf.new(setup=True)
    msp2 = out.modelspace()

    # One polyline per entity (keeps structure; joining comes next step)
    for pts in outlines:
        msp2.add_lwpolyline(pts, close=False)

    out.saveas(args.output_dxf)
    print("OK:", args.output_dxf)


if __name__ == "__main__":
    main()


