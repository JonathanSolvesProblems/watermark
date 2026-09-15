// RenoScout camera riser
// Lifts the camera head off the deck to room-viewing height so it frames walls,
// not the floor. Bottom flange bolts to the chassis M3 grid; the camera mount or
// pan/tilt head bolts to the top flange. Hollow centre = cable pass-through.
//
// SUPPORT-FREE BY DESIGN: the column flares out to the top flange at ~42 deg (under
// the 45 deg overhang limit), so it prints clean on DEFAULT settings with NO supports
// and no stringing. (The first version had a flat top ledge overhanging the column,
// which is what strung. Rule for all future parts: chamfer/flare instead of a flat
// overhang, keep every unsupported face within 45 deg of vertical.)
//
// OpenSCAD -> F6 -> Export STL. Cura: default profile, NO supports, brim optional.
// Prints upright, bottom flange on the bed.

riser_h  = 90;    // total height off the deck (Z; well under the 280 mm limit)
col      = 30;    // column outer size (square)
wall     = 3;     // column wall thickness
flange   = 55;    // flange plate size (square; fits the 225 bed easily)
flange_t = 4;     // flange thickness
taper_h  = 14;    // height of the 45 deg flare (>= (flange-col)/2 keeps it <=45 deg)
bore_d   = 16;    // cable pass-through bore
hole_d   = 3.4;   // M3 clearance
hole_in  = 9;     // how far the corner holes sit in from the flange edge
$fn      = 48;

col_h = riser_h - 2 * flange_t - taper_h;   // straight hollow column section

module flange_plate()
  difference() {
    translate([-flange / 2, -flange / 2, 0]) cube([flange, flange, flange_t]);
    for (x = [-1, 1], y = [-1, 1])
      translate([x * (flange / 2 - hole_in), y * (flange / 2 - hole_in), -1])
        cylinder(d = hole_d, h = flange_t + 2);
    translate([0, 0, -1]) cylinder(d = bore_d, h = flange_t + 2);   // cable bore
  }

// bottom flange (bolts down to the chassis grid)
flange_plate();

// hollow column
translate([0, 0, flange_t - 0.01])
  difference() {
    translate([-col / 2, -col / 2, 0]) cube([col, col, col_h + 0.02]);
    translate([-(col / 2 - wall), -(col / 2 - wall), -1]) cube([col - 2 * wall, col - 2 * wall, col_h + 2]);
  }

// 45 deg flare from column width up to flange width (self-supporting), cable bore
translate([0, 0, flange_t + col_h - 0.01])
  difference() {
    hull() {
      linear_extrude(0.1) square(col, center = true);
      translate([0, 0, taper_h]) linear_extrude(0.1) square(flange, center = true);
    }
    translate([0, 0, -1]) cylinder(d = bore_d, h = taper_h + 2);
  }

// top flange (camera mount / pan-tilt head bolts on)
translate([0, 0, riser_h - flange_t]) flange_plate();
