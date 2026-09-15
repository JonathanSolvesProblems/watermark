# hardware/

OpenSCAD sources for every printed part. All of them print on the Elegoo Neptune 3 Pro
with Cura defaults, PLA, **no supports**: every unsupported face is within 45 degrees
of vertical by design. Flat parts never string; the riser flares instead of ledging.

| Part | File | Status |
|---|---|---|
| Chassis plate, 190 x 150 x 4 mm, 4WD zip-tie motor slots, M3 grid | `watermark_chassis.scad` | Printed (Aug 5). Dry-fit passed. |
| Camera riser, 90 mm, hollow, 42 degree flare | `camera_riser.scad` | Printed (Aug 7). |
| Moisture wand paddle, 210 x 35 x 4 mm, zip-tie slots for DHT11 + water sensor + HC-SR04 | `moisture_wand.scad` | Printed (Aug 7). |
| **Ring Indoor Cam cradle** for the riser's top flange | `ring_cam_cradle.scad` | New. Measure `cam_base_d` before printing. |

## Ring Indoor Cam cradle

1. Measure the camera base where it touches the desk (diameter, or width if square).
   Put the number in `cam_base_d` at the top of the file.
2. OpenSCAD: F6, then File > Export > STL. The console prints the footprint and height.
3. Cura: defaults, no supports, brim optional. Flange down.
4. Fasten with four **M4 x 12 self-tapping** screws down through the counterbores into
   the riser's holes. M3 will not bite a 3.4 mm hole in PLA; M4 does.
5. Cable out the rear notch to the 5 V power bank on the deck. Zip-tie slots take a
   strap over the base if the route has bumps.

## Camera height

The riser puts the lens about 12 cm above the deck, which on this chassis is roughly
16 cm off the floor. That frames a baseboard and 1 to 2 m of floor in front of the
rover, which is what a flood at a water heater looks like. If the target is a wall
stain rather than a floor, tilt the camera's own swivel; do not raise the riser (it
was designed at 90 mm to stay stiff without supports).

## Line sensors and wand

The three TCRT5000 boards mount under the front edge of the chassis on the existing
zip-tie slots, 12 to 15 mm apart, 5 to 8 mm above the floor. The wand paddle hangs
its water probe at the very front, 2 to 3 mm above the floor, ahead of the sensors,
so wet stops the rover before the wheels reach the water.
