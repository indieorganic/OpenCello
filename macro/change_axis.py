import FreeCAD as App
import Part
import ImportGui

DOC = App.ActiveDocument

OUT_STEP = "./TOP_PLATE_oriented.step"

sel = App.Gui.Selection.getSelection()
if not sel:
    raise RuntimeError("Select the TOP_PLATE object before running.")
src = sel[0]
shape = src.Shape
if shape.isNull():
    raise RuntimeError("Selected object has no valid Shape.")

bb = shape.BoundBox
L = {"X": bb.XLength, "Y": bb.YLength, "Z": bb.ZLength}

# Identify thickness (smallest), length (largest), width (middle)
axes_sorted = sorted(L.items(), key=lambda kv: kv[1])  # smallest->largest
thick_axis = axes_sorted[0][0]
len_axis   = axes_sorted[2][0]
wid_axis   = axes_sorted[1][0]

App.Console.PrintMessage(f"Detected: thickness={thick_axis} length={len_axis} width={wid_axis}\n")

# Create a copy object we can transform
obj = DOC.addObject("Part::Feature", "TOP_PLATE_ORIENTED")
obj.Shape = shape.copy()
DOC.recompute()

# We want: thickness -> Z, length -> X
# We'll build a rotation that maps current axes into desired axes.
# Use a Placement that rotates basis vectors.
#
# Build mapping vectors:
axis_vec = {
    "X": App.Vector(1,0,0),
    "Y": App.Vector(0,1,0),
    "Z": App.Vector(0,0,1)
}

v_len   = axis_vec[len_axis]
v_thick = axis_vec[thick_axis]
v_wid   = axis_vec[wid_axis]

# Desired basis:
# X' (new X) = old length axis
# Z' (new Z) = old thickness axis
# Y' (new Y) = old width axis
# This is an orthonormal basis if the axes are perpendicular (they are for bbox).
Xn = v_len
Zn = v_thick
Yn = v_wid

# Construct rotation from old basis -> new basis
# FreeCAD rotation can be made from two vectors; we do it in two steps:
# Step1: rotate v_len onto X axis
rot1 = App.Rotation(v_len, App.Vector(1,0,0))
# Apply rot1 to thick axis, then rotate that onto Z axis without disturbing X
vth1 = rot1.multVec(v_thick)
rot2 = App.Rotation(vth1, App.Vector(0,0,1))

rot = rot2.multiply(rot1)

# Apply rotation about the object's center to keep it near origin
c = App.Vector(
    0.5*(bb.XMin+bb.XMax),
    0.5*(bb.YMin+bb.YMax),
    0.5*(bb.ZMin+bb.ZMax),
)

pl = App.Placement()
pl.Base = App.Vector(0,0,0)
pl.Rotation = rot

# Move to origin: translate to -center, rotate, translate back to origin (0,0,0)
# Easiest: set placement to rotate then translate by -rot*center
c_rot = rot.multVec(c)
obj.Placement = App.Placement(App.Vector(-c_rot.x, -c_rot.y, -c_rot.z), rot)

DOC.recompute()

# Export as STEP
ImportGui.export([obj], OUT_STEP)
App.Console.PrintMessage(f"Exported oriented STEP: {OUT_STEP}\n")
