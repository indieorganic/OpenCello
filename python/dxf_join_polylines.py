import ezdxf

def join_dxf_contour_final(input_file, output_file, tol=0.01):
    try:
        doc = ezdxf.readfile(input_file)
        msp = doc.modelspace()
        
        # 1. Collect all points from all entities
        all_segments = []
        entities = list(msp.query('LWPOLYLINE LINE'))
        
        for e in entities:
            if e.dxftype() == 'LINE':
                all_segments.append([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
            elif e.dxftype() == 'LWPOLYLINE':
                # Convert the internal points to a list of (x, y) tuples
                all_segments.append([(p[0], p[1]) for p in e.get_points()])
            msp.delete_entity(e)

        if not all_segments:
            print("No segments found.")
            return

        # 2. Re-order segments to form a logical chain
        # We start with the first segment and look for anything that touches its ends
        path = list(all_segments.pop(0))
        
        while all_segments:
            found = False
            for i, seg in enumerate(all_segments):
                # Helper function to check if two points are close
                def dist_sq(p1, p2):
                    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

                # Check all 4 connection possibilities (Start-Start, Start-End, etc.)
                if dist_sq(path[-1], seg[0]) < tol**2:
                    path.extend(seg[1:])
                    all_segments.pop(i); found = True; break
                elif dist_sq(path[-1], seg[-1]) < tol**2:
                    path.extend(reversed(seg[:-1]))
                    all_segments.pop(i); found = True; break
                elif dist_sq(path[0], seg[-1]) < tol**2:
                    path = seg[:-1] + path
                    all_segments.pop(i); found = True; break
                elif dist_sq(path[0], seg[0]) < tol**2:
                    path = list(reversed(seg[1:])) + path
                    all_segments.pop(i); found = True; break
            
            if not found:
                print(f"Warning: Discontinuity detected. {len(all_segments)} pieces left over.")
                break

        # 3. Save as a single closed polyline
        msp.add_lwpolyline(path, dxfattribs={'closed': 1})
        doc.saveas(output_file)
        print(f"Success! Saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

join_dxf_contour_final('back_flat.dxf', 'back_flat_joined.dxf')

