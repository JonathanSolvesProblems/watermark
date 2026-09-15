// RenoScout chassis plate
// Designed to fit the Elegoo Neptune 3 Pro (225 x 225 mm bed) and your exact parts:
// 4x yellow TT gear motors, 65 mm wheels, Raspberry Pi 4, L298N, 4xAA holder.
//
// It is JUST the chassis plate (no wheels — you already have those). You zip-tie the
// TT motors along the sides and standoff/zip-tie the Pi + battery + L298N onto the grid.
//
// HOW TO USE:
//   1. Install OpenSCAD (free: openscad.org) — or use any online .scad renderer.
//   2. Open this file, press F6 to render, then File > Export > Export as STL.
//   3. Slice in Cura: PLA, 0.2 mm layer, ~25% infill, NO supports, brim recommended.
//   4. It's ~190 x 150 mm, so it fits your 225 bed with room to spare.
//
// ASSEMBLY (4WD): flip the plate over, zip-tie two TT motors to each long edge
// (front + back), shafts pointing OUT so the wheels stick out the sides and clear
// the plate. Then mount the Pi, L298N, and battery holder on top using the hole grid
// (M3 standoffs or zip-ties). No rear caster needed for 4WD.
// (For 2WD instead: use 2 motors at the front + a small skid/caster at the back.)

// ---------------- parameters (tweak freely) ----------------
L      = 190;   // length, front-back (X). Fits the 225 bed.
W      = 150;   // width, left-right (Y). Wide enough for TT motors both sides + wheel clearance.
T      = 4;     // thickness. Rigid enough to carry the Pi + battery.
R      = 10;    // corner radius.

hole_d = 3.4;   // M3 clearance holes (electronics standoffs / zip-ties).
grid   = 20;    // mounting-hole grid spacing.
margin = 12;    // keep features this far in from the edge.

slot_w = 4;     // zip-tie slot width (fits a ~3 mm zip tie).
slot_l = 14;    // zip-tie slot length.
$fn    = 32;

// ---------------- helpers ----------------
module rrect(l, w, t, r)
  hull() for (x = [r, l - r], y = [r, w - r]) translate([x, y]) cylinder(r = r, h = t);

module slot()  // rounded zip-tie slot, long axis along X
  hull() for (x = [slot_w / 2, slot_l - slot_w / 2]) translate([x, 0, -1]) cylinder(d = slot_w, h = T + 2);

// ---------------- build ----------------
difference() {
  rrect(L, W, T, R);

  // mounting-hole grid across the whole plate (electronics + zip-tie points)
  for (x = [margin : grid : L - margin], y = [margin : grid : W - margin])
    translate([x, y, -1]) cylinder(d = hole_d, h = T + 2);

  // two rows of zip-tie slots near EACH long edge -> strap the TT motors at two points
  for (y = [margin, margin + 45, W - margin - 45 - slot_w, W - margin - slot_w])
    for (x = [margin : 24 : L - margin - slot_l])
      translate([x, y]) slot();
}
