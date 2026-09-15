// Watermark: Ring Indoor Cam (2nd gen) cradle for the camera riser.
//
// Sits on the riser's top flange (55 x 55 mm, four 3.4 mm holes 9 mm in from the
// edges, i.e. at +/-18.5 mm) and holds the camera's swivel base in a shallow cup.
// The cup is oversized and four small ribs take up the slack, so one measured
// number (cam_base_d) is all that has to be right. Cable leaves through the rear
// notch. Two zip-tie slots per side let a strap go over the base on a bumpy route.
//
// Fastening: four M4 x 12 self-tapping screws down through the counterbores in the
// cup floor into the riser's 3.4 mm holes (M4 bites PLA in a 3.4 mm hole; M3 does
// not). Heads sit below the cup floor so the camera base rests flat.
//
// SUPPORT-FREE: flange on the bed, vertical walls, counterbore ceilings are 9 mm
// bridges. Nothing overhangs past 45 deg. Prints on the Neptune 3 Pro defaults.
//
// MEASURE FIRST: cam_base_d is the diameter (or width, if square) of the camera's
// base where it touches the desk. Set it, F6, export STL, Cura defaults, no supports.

cam_base_d   = 50;     // MEASURE: Ring Indoor Cam 2nd gen base, mm (nominal ~48-50)
base_clear   = 0.6;    // radial clearance the ribs close down to
pocket_d     = 56;     // cup inside diameter (bigger than the base; ribs centre it)
wall         = 3;      // cup wall
cup_h        = 14;     // pocket depth
floor_t      = 4;      // pocket floor thickness (screw heads live in it)
flange       = 55;     // riser top flange size
flange_t     = 4;      // flange thickness
hole_in      = 9;      // hole inset, matches camera_riser.scad
screw_d      = 4.3;    // M4 clearance through the cradle
head_d       = 9;      // M4 pan head counterbore
head_h       = 3.2;    // counterbore depth
notch_w      = 9;      // rear cable notch width
rib_w        = 2.5;    // centering rib width
slot_w       = 4;      // zip-tie slot width
slot_h       = 7;      // zip-tie slot height
$fn          = 72;

outer_d  = pocket_d + 2 * wall;
rib_len  = (pocket_d - cam_base_d) / 2 - base_clear;   // how far each rib reaches in
hole_r   = flange / 2 - hole_in;                       // 18.5 mm from centre on x and y
total_h  = flange_t + floor_t + cup_h;

// ---- flange: bolts to the riser ----
module flange_plate()
  difference() {
    translate([-flange / 2, -flange / 2, 0]) cube([flange, flange, flange_t]);
    for (x = [-1, 1], y = [-1, 1])
      translate([x * hole_r, y * hole_r, -1]) cylinder(d = screw_d, h = flange_t + 2);
  }

// ---- cup: its own z = 0 is the top of the flange ----
module cup() {
  difference() {
    cylinder(d = outer_d, h = floor_t + cup_h);
    // the pocket
    translate([0, 0, floor_t]) cylinder(d = pocket_d, h = cup_h + 1);
    // screw holes and counterbores through the floor; heads end below the floor top
    for (x = [-1, 1], y = [-1, 1]) {
      translate([x * hole_r, y * hole_r, -1]) cylinder(d = screw_d, h = floor_t + 2);
      translate([x * hole_r, y * hole_r, floor_t - head_h]) cylinder(d = head_d, h = head_h + 1);
    }
    // rear cable notch (-Y): through the wall and the floor
    translate([-notch_w / 2, -outer_d / 2 - 1, -1]) cube([notch_w, wall + 4, floor_t + cup_h + 2]);
    // zip-tie slots through the +/-X walls near the rim
    for (x = [-1, 1], y = [-1, 1])
      translate([x * (outer_d / 2 - wall / 2) - (wall + 2) / 2, y * 12 - slot_w / 2, floor_t + cup_h - slot_h - 2])
        cube([wall + 2, slot_w, slot_h]);
  }
  // centering ribs on the inside wall, at 45 deg so they miss the notch and the slots
  if (rib_len > 0.4)
    for (a = [45, 135, 225, 315])
      rotate([0, 0, a])
        translate([pocket_d / 2 - rib_len, -rib_w / 2, floor_t - 0.01])
          cube([rib_len + 0.5, rib_w, cup_h * 0.7]);
}

flange_plate();
translate([0, 0, flange_t - 0.01]) cup();

echo(str("cradle: ", outer_d, " mm round, ", total_h, " mm tall, ribs reach ", rib_len, " mm, heads ",
         head_h, " mm below the floor"));
