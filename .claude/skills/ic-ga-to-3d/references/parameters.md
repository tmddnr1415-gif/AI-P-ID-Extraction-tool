# Anatomy parameter dictionary

Generated — rebuild with `node ic-3d-builder/dev/spec.mjs params`. Source: `ic-3d-builder/src/anatomy.js`.

## `valve` — Valve (CV · MOV · Manual · PSV)

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Tag No. |
| `body` |  | globe, gate, ball, butterfly, psv | Body type — globe / gate / ball / butterfly / psv (angle-pattern spring-loaded safety valve) |
| `operator` |  | handwheel, lever, gear, pneumatic_diaphragm, pneumatic_rotary, electric, spring | Operator — handwheel, lever, gear (worm gear), pneumatic_diaphragm (spring & diaphragm CV), pneumatic_rotary (rack & pinion / scotch yoke), electric (MOV), spring (PSV) |
| `service` |  | control, on_off | Service — control → globe face-to-face per ISA-75.08.01 and cage-guided trim |
| `nps` | in |  | Size NPS (inlet) |
| `cls` |  | 150, 300 | Pressure class (inlet) |
| `outlet_nps` | in |  | Outlet NPS |
| `outlet_cls` |  | 150, 300 | Outlet class |
| `bore` |  | full, reduced | Ball bore |
| `ftf` | mm |  | Face-to-face — Flange face to flange face |
| `cti` | mm |  | Centre to inlet face — Outlet centreline to inlet flange face (vertical) |
| `cto` | mm |  | Centre to outlet face — Inlet centreline to outlet flange face (horizontal) |
| `body_h` | mm |  | Body height (CL → bonnet face) |
| `body_w` | mm |  | Body max. width |
| `bonnet_h` | mm |  | Bonnet / neck height — Bonnet flange to yoke/operator mounting face (PSV: spring bonnet height) |
| `port_d` | mm |  | Port / seat bore — Seat ring bore / ball bore / nozzle bore |
| `stem_d` | mm |  | Stem / shaft diameter |
| `pipe_stub` | mm |  | Reference pipe length — 0 = hide |
| `yoke_h` | mm |  | Yoke / bracket height |
| `act_d` | mm |  | Actuator diameter / width |
| `act_h` | mm |  | Actuator height |
| `act_l` | mm |  | Cylinder length (rotary) |
| `hw_d` | mm |  | Handwheel diameter |
| `lever_l` | mm |  | Lever length |
| `stem_ext` | mm |  | Stem rise (rising stem, open) |
| `positioner` |  | true, false | Positioner |
| `cv_handwheel` |  | true, false | Top-mounted handwheel |
| `psv_lever` |  | true, false | Lifting lever |
| `overall_h` | mm |  | Overall height (CL → top) — If the drawing only gives the overall height, enter it here: estimated heights are scaled to match |

## `cabinet` — System Cabinet

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Cabinet No. |
| `bays` |  |  | Number of bays |
| `w` | mm |  | Width W (per bay) |
| `h` | mm |  | Height H (excl. plinth) |
| `d` | mm |  | Depth D |
| `plinth_h` | mm |  | Plinth height |
| `doors` |  | 1, 2 | Front doors per bay |
| `rear_door` |  | true, false | Rear door |
| `door_open` | ° |  | Door opening angle |
| `louvers` |  | true, false | Door louvres / filter fans |
| `fan` |  | true, false | Roof fan |
| `lifting_eyes` |  | true, false | Lifting eye bolts |
| `mounting_plate` |  | true, false | Mounting plate |
| `modules` |  |  | DIN rail / I/O rows |
| `gland_plate` |  | true, false | Bottom gland plate |
| `clearance` | mm |  | Front maintenance clearance — 0 = hide |

## `hookup` — Instrument Hook-up

| key | 단위 | 선택지 | 의미 |
|---|---|---|---|
| `tag` |  |  | Tag No. |
| `inst` |  | PT, DPT, LT_DP, FT_DP | Instrument — PT = pressure, DPT = differential pressure, LT_DP = DP level (two vessel nozzles), FT_DP = DP flow (orifice taps) |
| `service` |  | gas, liquid, steam | Fluid — gas → instrument above tap; liquid/steam → instrument below tap |
| `proc_nps` | in |  | Process pipe NPS |
| `pipe_el` | mm |  | Pipe centreline elevation |
| `tap` |  | top, side, bottom, side45 | Tap orientation |
| `tap_sep` | mm |  | HP–LP tap separation — DP flow: orifice flange tap spacing; DP level: nozzle elevation difference |
| `mount` |  | stand, close_coupled | Mounting |
| `stand_h` | mm |  | Stand height |
| `stand_dx` | mm |  | Stand offset X (along pipe) |
| `stand_dz` | mm |  | Stand offset Z (from pipe) |
| `tube_od` | mm |  | Impulse tube OD |
| `slope` | 1:x |  | Tubing slope — Minimum slope of horizontal runs; 1:12 is typical |
| `root_valve` |  | true, false | Root valve |
| `manifold` |  | none, 2V, 3V, 5V | Manifold |
| `drain` |  | true, false | Drain / vent valve |
| `sunshade` |  | true, false | Sunshade |


Presets:
```
cv_globe   valve    Control valve — Globe (spring & diaphragm)
cv_ball    valve    Control valve — Ball (pneumatic rotary)
cv_bfv     valve    Control valve — Butterfly (pneumatic rotary)
mov_gate   valve    MOV — Gate
mov_globe  valve    MOV — Globe
mov_ball   valve    MOV — Ball
mov_bfv    valve    MOV — Butterfly
man_gate   valve    Manual — Gate (OS&Y handwheel)
man_globe  valve    Manual — Globe (handwheel)
man_ball   valve    Manual — Ball (lever)
man_bfv    valve    Manual — Butterfly (gear)
psv        valve    PSV — Spring-loaded (angle)
cabinet    cabinet  System cabinet
hook_pt    hookup   Hook-up — PT on pipe stand
hook_dpt   hookup   Hook-up — DP flow (orifice, close-coupled)
hook_lt    hookup   Hook-up — DP level (vessel)
```

Part catalogue (part_id — used to link a drawing parts list to 3D parts):

- **valve**: `body` Body · `seat_ring` Seat ring · `cage` Cage · `plug` Valve plug · `stem` Valve stem · `bonnet_gasket` Bonnet gasket · `bonnet` Bonnet · `bonnet_bolting` Bonnet studs & nuts · `packing` Packing set · `gland` Packing follower · `gland_flange` Packing flange · `gland_studs` Packing flange studs & nuts · `yoke` Yoke · `stem_connector` Stem connector · `travel_indicator` Travel indicator & scale · `actuator_stem` Actuator stem · `lower_casing` Lower diaphragm casing · `spring` Actuator spring · `diaphragm_plate` Diaphragm plate (head) · `diaphragm` Diaphragm · `upper_casing` Upper diaphragm casing · `casing_bolts` Casing cap screws & nuts · `handwheel` Handwheel · `positioner_bracket` Positioner mounting bracket · `positioner` Digital valve positioner · `airset` Air filter regulator · `tubing` Instrument tubing · `bolting_in` Inlet flange studs & nuts · `bolting_out` Outlet flange studs & nuts · `body_connector` Body connector (end piece) · `body_bolting` Body bolting · `mounting_pad` Top flange (ISO 5211 pad) · `seats` Seats · `ball` Ball · `thrust_washer` Stem thrust washer · `stem_seal` Stem seals (O-rings / packing) · `bracket` Mounting bracket · `coupling` Drive coupling · `actuator` Actuator housing (rack & pinion) · `end_cap_l` End cap / spring cartridge (left) · `end_cap_r` End cap / spring cartridge (right) · `indicator` Visual position indicator · `solenoid` Solenoid valve (NAMUR) · `liner` Seat liner · `disc` Disc · `taper_pins` Disc taper pins · `shaft_lower` Lower shaft · `bushings` Shaft bushings · `shaft_upper` Upper shaft · `seat_rings` Seat rings · `wedge` Wedge (gate) · `thrust_base` Thrust base (type A) · `drive_bush` Drive bush (stem nut) · `gearcase` Main gearcase (worm drive) · `control_unit` Control unit & display · `motor` Motor · `declutch` Declutch lever · `hw_shaft` Handwheel shaft · `terminal_cover` Terminal compartment & cable entries · `stem_cover` Stem protection tube · `trunnion` Lower trunnion & cover · `yoke_sleeve` Yoke sleeve (stem nut) · `hw_nut` Handwheel nut · `lever_head` Wrench head & stop plate · `lever` Lever handle · `gearbox` Worm gearbox · `gear_indicator` Position indicator · `input_shaft` Input shaft · `nozzle` Nozzle · `adjusting_ring` Adjusting (blowdown) ring · `disc_holder` Disc holder · `guide` Guide · `spindle` Spindle · `lower_washer` Lower spring washer · `upper_washer` Upper spring washer · `bonnet_studs` Bonnet studs & nuts · `adjusting_screw` Adjusting screw & lock nut · `cap` Lifting lever cap
- **cabinet**: `plinth` Plinth (base frame) · `frame` Frame · `side_panel_l` Side panel (left) · `side_panel_r` Side panel (right) · `roof` Roof plate · `rear` Rear door · `doors` Front door(s) · `handles` Handles & locks · `louvers` Louvres / filter fans · `gland_plate` Gland plate · `lifting_eyes` Lifting eye bolts · `mounting_plate` Mounting plate · `din_rails` DIN rails & wiring duct · `modules` I/O modules & terminals
- **hookup**: `transmitter` Pressure transmitter · `manifold` 2V valve manifold · `root_valve0` Root valve · `root_valve0_hw` Root valve handle · `drain` Drain valve · `tubing0` Impulse tubing · `stand` 2" pipe stand · `ubolt` Mounting bracket & U-bolts · `orifice` Orifice flange set & plate · `root_valve1` Root valve (LP) · `root_valve1_hw` Root valve (LP) handle · `tubing1` Impulse tubing (LP)
