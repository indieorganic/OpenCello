# OpenCello
My weekend project to build a cello with the help of CNC and laser cut.

Step 1: Find a model.

  - Henry A. Strobel: [Cello Making: For Use with Violin Making, Step by Step](https://www.henrystrobel.com)

Step 2: Build the inner template.

  - Online resource: [A full size (755mm) cello assembly](https://grabcad.com/library/a-full-size-755mm-cello-assembly-1)

  - CAD Tool: [FreeCad](https://www.freecad.org/index.php?lang=en)
    
  - Generate 2D DXF from STEP with this example macro : [cello_inner_mold_from_step
](https://github.com/indieorganic/OpenCello/blob/main/FreeCAD/cello_inner_mold_from_step)

| Parameter      | Value                                    |
| -------------- | ---------------------------------------- |
| Rib thickness  | **2.0 mm**                               |
| Glue clearance | **0.2 mm**                               |
| Mold offset    | **2.2 mm inward**                        |
| Mold thickness | **18 mm plywood**                        |
| Mold type      | **inner mold**                            

   - Measuring in FreeCAD:
     
| Check       | Expected                     |
| ----------- | ---------------------------- |
| Body length | ~755 mm                      |
| Upper bout  | ~340 mm                      |
| C-bout      | ~230 mm                      |
| Lower bout  | ~440 mm                      |
| Offset      | Exactly 2.2 mm               |
| Curves      | Closed, no self-intersection |





