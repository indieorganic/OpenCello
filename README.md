# OpenCello
My weekend project to build a cello with the help of CNC and laser cut.

Step 1: Find a model.

  - Henry A. Strobel: [Cello Making: For Use with Violin Making, Step by Step](https://www.henrystrobel.com)

Step 2: Build the template for inner mold or top/back.

  - Online resource: [A full size (755mm) cello assembly](https://grabcad.com/library/a-full-size-755mm-cello-assembly-1)

  - CAD Tool for STEP: [FreeCad](https://www.freecad.org/index.php?lang=en)
  - Measuring in FreeCAD:
     
| Check       | Expected                     |
| ----------- | ---------------------------- |
| Body length | ~755 mm                      |
| Upper bout  | ~340 mm                      |
| C-bout      | ~230 mm                      |
| Lower bout  | ~440 mm                      |
    
  - Generate 2D DXF from STEP: Change the axis to let top plate face to z-axis. (Try the macro "change_axis")
  - CAD Tool for DXF: [LibreCAD](https://librecad.org)
  - Editing DXF to get the outline for laser cut:
     1. Select and delete intenal enties with LibreCAD.
     2. pip install ezdxf (We need python3, too).
     3. Inspect the enties of DXF: using python/dxf_inspect.py.
     4. Flatten the DXF into polylines: using python/dxf_flatten_to_polyline.py.
     5. Convert the remaining outline segments into one polyline: using python/dxf_join_polylines.py.
     6. Offset inward by 2.2 mm for inner mold: using python/dxf_offset.py. 
     7. Inspect and export a laser-safe DXF: Save As DXF R2000 (usually safest for CAM).
   
| Parameter      | Value                                    |
| -------------- | ---------------------------------------- |
| Rib thickness  | **2.0 mm**                               |
| Glue clearance | **0.2 mm**                               |
| Mold offset    | **2.2 mm inward**                        |
| Mold thickness | **18 mm plywood**                        |
| Mold type      | **inner mold**                            





