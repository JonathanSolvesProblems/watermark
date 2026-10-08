// RenoScout moisture wand
// A flat paddle that carries the moisture-mapping sensors, the differentiator a
// depth camera can't do: DHT11 humidity/temp + a water-level sensor at the tip +
// HC-SR04 for stand-off distance. Sensors strap on with zip ties (like the chassis)
// so any module fits, with no tight pockets to fail.
//
// OpenSCAD -> F6 -> Export STL. Cura: PLA, 0.2mm, 20% infill, NO supports, brim.
// Prints flat, ~210 x 35 x 4 mm (fits the 225 bed). Water sensor at the tip (touches
// damp surfaces), HC-SR04 near the tip (faces forward), DHT11 mid-handle (open air).
// Run the wires down between the slots to the Pi/Arduino.

Lw     = 210;  // length (fits the 225 bed)
Ww     = 35;   // width
Tw     = 4;    // thickness
Rw     = 8;    // grip / corner radius
hole_d = 3.4;  // M3 hang hole
slot_w = 4;    // zip-tie slot width
slot_l = 14;   // zip-tie slot length
$fn    = 32;

module rrect(l, w, t, r)
  hull() for (x = [r, l - r], y = [r, w - r]) translate([x, y]) cylinder(r = r, h = t);

module slot()  // rounded zip-tie slot, long axis along X
  hull() for (x = [slot_w / 2, slot_l - slot_w / 2]) translate([x, 0, -1]) cylinder(d = slot_w, h = Tw + 2);

difference() {
  rrect(Lw, Ww, Tw, Rw);

  // paired zip-tie slots along the wand -> strap any sensor module anywhere
  for (x = [22 : 26 : Lw - 28])
    for (y = [7, Ww - 7 - slot_w])
      translate([x, y]) slot();

  // hang / lanyard hole at the grip end
  translate([Rw + 4, Ww / 2, -1]) cylinder(d = hole_d, h = Tw + 2);
}
