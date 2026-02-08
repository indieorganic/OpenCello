import ezdxf
from collections import Counter
import sys

doc = ezdxf.readfile(sys.argv[1])
msp = doc.modelspace()

c = Counter(e.dxftype() for e in msp)
print("Entity counts:")
for k, v in c.most_common():
    print(f"  {k:12s} {v}")

# Print a few biggest polylines by bbox span (helps if outline is already a polyline)
polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
print(f"\nLWPOLYLINE count: {len(polys)}")
for i, e in enumerate(polys[:10]):
    try:
        ext = e.dxf.extrusion if e.dxf.hasattr("extrusion") else None
        bb = e.bbox()
        dx = bb.size.x
        dy = bb.size.y
        closed = bool(e.closed)
        print(f"  [{i}] closed={closed} span=({dx:.2f},{dy:.2f}) extrusion={ext}")
    except Exception as ex:
        print(f"  [{i}] bbox failed: {ex}")
