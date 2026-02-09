import ezdxf
from ezdxf.math import offset_vertices_2d, Vec2

def join_and_offset_dxf(input_file, output_file, offset_dist=2.0, tol=0.01):
    try:
        doc = ezdxf.readfile(input_file)
        msp = doc.modelspace()
        
        # 1. Collect and join segments (as we did previously to fix the "extra lines")
        all_segments = []
        entities = list(msp.query('LWPOLYLINE LINE'))
        for e in entities:
            if e.dxftype() == 'LINE':
                all_segments.append([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
            elif e.dxftype() == 'LWPOLYLINE':
                all_segments.append([(p[0], p[1]) for p in e.get_points()])
            msp.delete_entity(e)

        if not all_segments: return

        path = list(all_segments.pop(0))
        while all_segments:
            found = False
            for i, seg in enumerate(all_segments):
                def dist_sq(p1, p2): return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
                if dist_sq(path[-1], seg[0]) < tol**2:
                    path.extend(seg[1:]); all_segments.pop(i); found = True; break
                elif dist_sq(path[-1], seg[-1]) < tol**2:
                    path.extend(reversed(seg[:-1])); all_segments.pop(i); found = True; break
                elif dist_sq(path[0], seg[-1]) < tol**2:
                    path = seg[:-1] + path; all_segments.pop(i); found = True; break
                elif dist_sq(path[0], seg[0]) < tol**2:
                    path = list(reversed(seg[1:])) + path; all_segments.pop(i); found = True; break
            if not found: break

        # 2. Perform the Offset
        # offset_vertices_2d expects a list of Vec2 objects
        vertices = [Vec2(p) for p in path]
        
        # We try positive and negative to ensure it goes 'inward'
        # Note: If the offset goes outward, change the sign of offset_dist
        offset_path = offset_vertices_2d(vertices, offset_dist, closed=True)

        # 3. Add both to the DXF
        # Original Joined Contour (White)
        msp.add_lwpolyline(vertices, dxfattribs={'closed': 1, 'color': 7})
        
        # Offset Contour (Red)
        msp.add_lwpolyline(offset_path, dxfattribs={'closed': 1, 'color': 1})

        doc.saveas(output_file)
        print(f"Success! Created joined contour with {offset_dist}mm offset in {output_file}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Try -2.0 for inward (depends on winding order)
join_and_offset_dxf('back_flat_joined.dxf', 'back_flat_offset.dxf', offset_dist=-4.7)

