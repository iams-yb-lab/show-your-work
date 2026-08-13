"""Assembly animation v2: copper laminate -> etched -> coated -> printed -> populated.

Where v1 (`animate_assembly.py`, kept as the baseline) starts from a finished board and
drops parts vertically onto a stationary PCB, this one fabricates the board on camera and
then flies the parts in laterally onto a *spinning* one. Both share `blender_scene.py` --
the import, the material corrections, the four-light studio and the exposure calibration
are all still there and unchanged.

    blender --background --factory-startup --python animate_assembly_v2.py -- \
        --pcb3d out/scene/pcb_purple_v2.pcb3d --parts out/scene/components_v2.json \
        --blend out/scene/anim_purple_v2.blend --outdir out/anim/purple_v2

Four ideas carry it, and each replaces something v1 could not do:

  Fabrication comes out of the real layer data, never out of an imitation. pcb2blender's
  board material is a `ShaderNodePcbShader` fed by eight float sockets -- F_Cu B_Cu F_Mask
  B_Mask F_SilkS B_SilkS F_Paste B_Paste -- which come from four rasterised layer images
  whose R channel is the front layer and G the back, on UVs that are a linear map of board
  XY. Rewiring those eight links through animated chains is enough to etch, coat, plate and
  print the actual board: the copper that survives is the copper KiCad plotted.

  The board is a rig, and it moves. BOARD_RIG parents the board, every component, every
  solder joint and the two mask films, so the whole assembly can spin while parts land on
  it. Its rotation is an analytic function of frame -- not a depsgraph query -- so the
  component solver can ask where the pads will be at frame 700 before anything is keyed.

  Parts fly in world space and land in board space. A flight is authored in the world (its
  entry direction comes from the camera's own basis at its entry frame, so it really does
  come in from the side of the frame) and baked back through the rig:
  basis(f) = P^-1 . R(f)^-1 . W(f). The land frame is then written from the part's *stored
  original floats*, so the landed board is bit-identical to the import whatever the flight
  did. Verified at the last frame before the render starts.

  The camera orbits in the board's own frame, and that one number is the shot. `orb` is
  the camera's azimuth *relative to the board's yaw*, which is what every board feature's
  screen position actually depends on -- the world frame only supplies the lights. The
  first cut of this file authored a world azimuth plus a `mix` fraction of the board's yaw
  the camera inherited, and that was the bug: what the viewer sees is the difference of the
  two, so both channels were smooth and C2 while their difference reversed direction six
  times. A reversal of screen direction inside a shot reads as a cut. `orb` is monotone
  from frame 1 to the end, and the board's yaw is then free to serve the lighting.

`--plan-only` evaluates the whole schedule, the rig and the camera without importing the
board, and prints the diagnostics that matter -- peak angular rates, which face is towards
the camera, floor clearance. It runs in seconds, which is the only reason the tables below
could be tuned at all.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import re
import sys
import tomllib
import zipfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).parent))
import blender_scene as studio  # noqa: E402

FPS = 30
LOOK = "product"
BACKDROP = "mood"
SEED = 20260811

# The board floats: the storyboard needs it clear of the floor for the swarm phase, and the
# board tips a long way over to show its bottom copper, which puts one edge well below its own
# plane. build_backdrop() already takes this as `float_mm`. The camera no longer needs the
# clearance for itself -- it used to dip to elevation -17 for the same reveal, and now stays
# on its arc while the board does the turning; the margin here is what --plan-only reports as
# floor clearance, which went from 31 mm to 156 as a result.
FLOOR_DROP_MM = 118.0

# Shutter, as a fraction of the frame interval. v1 used 0.50; the board used to spin through
# its swarm phase at ~32 deg/s, which smeared a 0.25 mm trace across four pixels at 1440p, and
# 0.07 was what kept routing readable. Smear is the product of shutter and rate, and the peak
# rate is now 12.6 deg/s, so 0.12 is still ~40 % *less* smear than the frames that number was
# chosen against. What it buys is the judder a low shutter costs on a slow move.
SHUTTER = 0.12

# ------------------------------------------------------------------------------ timeline
#
# Frames, at 30 fps. Everything downstream is derived from these, so retiming happens here
# and nowhere else. Phases overlap where the storyboard asks them to. The last camera beat
# is the end of the piece -- see CAM_BEATS.
# The two etch fronts and the two film contacts are timed against the board's own roll --
# see RIG_BEATS and the facing profile --plan-only prints. The top front crosses while the top
# is held square to camera; the bottom front crosses inside the window where the underside is
# genuinely presented (facing past -0.35, f440-560), starting a little before it so the two
# overlap; the films then touch at facing +0.16 and +0.26, on the way back up. They used to
# touch at dead edge-on and that was wrong -- see RENDER-LOG.md.
F_COPPER_END = 170       # 0.00 -  5.67  unprocessed copper-clad, camera already moving
F_ETCH_TOP = (170, 330)  # 5.67 - 11.00  top etch front crosses the board
F_ETCH_BOT = (425, 545)  # 14.17 - 18.17  bottom front crosses it the other way
F_FILM_FLY = 525         # 17.50         the two mask films set off
F_FILM_CONTACT = (620, 640)   # top film touches, then the bottom one
F_HANDOFF = 24           # frames from contact to the board carrying its own mask
F_FILM_FADE = 30         # frames for an arriving film to come up from invisible
F_PADS = (664, 752)      # 22.13 - 25.07  mask openings develop, ENIG plates
F_SILK = (736, 846)      # 24.53 - 28.20  silkscreen widens and travels
# 92 frames of clear air between one hero landing and the next entrance. It is this long
# because it is not dead time: it is how long the camera takes to travel from the part that
# just landed to the pads of the next one, at a speed that reads as a move rather than a
# reposition. The ADC and the driver are 38 mm apart on the board and the driver and the
# Teensy 67 mm, so this is the number that sets the traverse.
F_HERO_GAP = 92
F_MIN_TAIL = 150         # the finale needs at least this long after the Teensy lands

# Etch geometry, in millimetres on the board. `phi` is the sweep axis: the front is a line
# of constant s = x*cos(phi) + y*sin(phi), so a rotated axis crosses the routing diagonally
# instead of marching along a board edge.
ETCH = dict(phi_top=22.0, phi_bot=201.0, width=9.0, wobble=5.0, wobble_scale=6.5)
# How far the aim actually follows the etch front, as a fraction of the front's own travel.
# Following it outright is what the first two drafts did, and the front runs to within 8 % of
# the board edge: with the frame 151-176 mm wide the aim swung +-69 mm, which walks half the
# board out of shot and back for no gain -- a fabrication beat only needs the focus to *shift*
# towards the region being etched. At 0.42 the aim travels +-29 mm, about a third of a
# half-frame, and the board stays in frame through both fronts. Same damping idea as
# `swarm_bias`, and for the same reason: an aim that commits to a trip has to undo it.
ETCH_AIM_BIAS = 0.42
# Morphology radii, in millimetres. PAD_R closes every mask opening on this board (the
# smallest is a 0.4 mm 0402 aperture, the largest a 1.85 mm through-hole disc), so openings
# grow from nothing out to their real shape. SILK_R is a little over half the thinnest
# stroke, so text and outlines widen from their skeleton rather than fading up.
PAD_R = 0.62
SILK_R = 0.13
TAPS = 8                 # ring taps for the morphology; at radius 0 they all coincide
# Half-widths of the travelling silkscreen and paste fronts, in mm: how much of the board is
# mid-transition at any moment. Wide enough to read as drawing rather than as a wipe.
SILK_RAMP = 14.0
PASTE_RAMP = 22.0

# Bare copper laminate, and the wet line at the etch front. Both sRGB; the surface-finish
# node wants linear, so hex2lin() converts. ENIG is the importer's own ENIG, untouched --
# it only appears once V_plate rides up during the pads phase, which is also when a real
# board gets plated.
COPPER_BARE = ("b0714e", 0.24, 0.85)    # colour, roughness, texture strength
COPPER_ETCH = ("6a4636", 0.52, 1.00)    # darker and rougher: copper going into solution

# The airborne film has no colour of its own: it reads the Solder Mask node's own Light
# Colour off the board material, so the sheet that lands and the mask it becomes are the
# same purple by construction, and a colour variant needs no edit here. Only its opacity
# while airborne is a choice.
FILM_ALPHA_AIR = 0.55

# -------------------------------------------------------------------------------- parts
#
# The three parts that get their own introduction, keyed on the part number in the board's
# Value field rather than on a designator -- designators get renumbered, and this repo has
# already moved one four times. Resolved to designators at runtime and printed.
HEROES = (
    ("adc", "AD7124"),      # AD7124-8BCPZ, the ADC
    ("driver", "MAX1968"),  # MAX1968EUI+T, the TEC driver
    ("mcu", "Teensy"),      # Teensy 4.1, the controller module
)

# Supporting waves, in the order the storyboard asks for and the only place it is written
# down. `start` and `span` are absolute frames -- the point of a fixed timeline is that a
# group's slot is legible here. Waves overlap slightly on purpose, so there is no dead air,
# while each group's bulk still lands before the next group's bulk sets off.
#
#   sub      regional sub-waves: the group is split into this many diagonal bands, each
#            arriving from its own side of the frame
#   travel   frames one part is in the air
#   rise     height above its pads it flies in at, in mm, before the final descent
#   reach    entry distance, as a multiple of the frame half-width at that moment
#   arc      tangential bulge, same units -- this is what makes the path curved
#   spin     yaw it turns through on the way in, degrees
#   tumble   rotation about the entry-perpendicular axis: the orientation correction that
#            reads as a part turning to face its own footprint
#   lift     extra mid-flight height, as a fraction of `rise`
#   settle   amplitude of the single small hop at the end, in mm (0 = none)
# and three more that only the heroes use, in HERO_MOVES: `approach`, `hover`, `hover_at`.
# `reach` scales the just-off-frame distance entry_basis solves, so 1.0 means "as close to the
# frame edge as still clears it" and larger values give the bigger parts a longer, more
# deliberate run in. It is not a distance.
#
# The *order* of the rows is not cosmetic either: sub-waves take their entry sectors from
# SECTORS in this order, so moving a row moves which side of the frame its parts fly in from.
WAVES = (
    # `rise` and `lift` are generous for the smallest parts on purpose. A 1 x 0.5 mm 0402 is
    # about five pixels at a 960-wide draft, and five grey pixels crossing a lit purple board
    # are invisible; the same five pixels against the dark studio read clearly. Flying the
    # passives well above the board's silhouette for most of the trip, then dropping, is what
    # makes the wave legible -- and it reads more like placement besides.
    # The waves are spread over 21 s here against v2's 9 -- but `travel` only grows from 34
    # frames to 58. The extra time is in the *spans*, not in the flights: slowing a 0402
    # down to match a longer piece turns placement into drifting, where a longer span keeps
    # each part purposeful and just lets more of them arrive. That distinction is the whole
    # answer to "make it longer without making it slow".
    ("resistors", dict(start=880, span=210, sub=4, travel=58, rise=26, reach=1.00,
                       arc=0.26, spin=14, tumble=22, lift=0.45, settle=0.0)),
    ("ceramics", dict(start=1010, span=230, sub=4, travel=58, rise=28, reach=1.02,
                      arc=0.30, spin=-16, tumble=26, lift=0.48, settle=0.0)),
    ("semis", dict(start=1210, span=84, sub=2, travel=60, rise=32, reach=1.06,
                   arc=0.34, spin=18, tumble=34, lift=0.40, settle=0.15)),
    ("power", dict(start=1270, span=96, sub=2, travel=66, rise=30, reach=1.10,
                   arc=0.36, spin=-20, tumble=30, lift=0.28, settle=0.25)),
    # Terminals now go *before* the headers rather than after them, and that is about the
    # camera rather than about the parts. The connector needs the frame to itself while it
    # lands -- see TARGET_BEATS -- and the aim cannot leave the swarm while the last screw
    # terminal is still coming down at the far end of the board, 150 mm from the connector.
    # Moved 82 frames earlier, the terminals land by 1427 and the headers by 1458, which
    # leaves the connector alone in the air from 1458 and the aim free from 1400.
    ("terminals", dict(start=1300, span=64, sub=1, travel=76, rise=38, reach=1.18,
                       arc=0.32, spin=-14, tumble=24, lift=0.26, settle=0.35)),
    ("headers", dict(start=1340, span=60, sub=1, travel=70, rise=34, reach=1.14,
                     arc=0.34, spin=16, tumble=26, lift=0.28, settle=0.30)),
    # Lands on 1524, and is the last thing to land: F_HERO_GAP and the three hero travels
    # are chained off that frame, so this row is what puts the ADC's landing on 1720.
    ("harting", dict(start=1440, span=0, sub=1, travel=84, rise=46, reach=1.24,
                     arc=0.30, spin=10, tumble=18, lift=0.24, settle=0.45)),
)

# Which parts belong to which group, tested against the board's own footprint field so the
# grouping is a fact about the part rather than a list to maintain. First match wins; the
# heroes are removed before any of this runs.
GROUP_TESTS = (
    ("resistors", ("Resistor_SMD:R_",)),
    ("ceramics", ("Capacitor_SMD:C_",)),
    ("semis", ("D_SOD", "LED-SMD", "SOT-23", "SOIC-8")),
    # Inductors, the bulk electrolytic, the slide switch and the three trimmers.
    ("power", ("IND-SMD", "CAP-SMD_BD", "SW-SMD", "RES-ADJ")),
    ("headers", ("PinHeader",)),
    ("terminals", ("TerminalBlock",)),
    ("harting", ("HARTING",)),
)

# The hero entrances. Each is a different shape of move, which is the requirement: the ADC
# arcs in from frame left and turns far enough to show its contacts, the driver comes in
# low, flat and fast from the right foreground, the Teensy makes the long one out of depth
# with real mass. `sector` is degrees about the camera's view axis -- 0 frame right, 180
# frame left, 90 behind the board, 270 in front of it.
#
# `approach` and `hover` are what make a hero landing a landing: the flight in is over at
# u = approach, the part then holds still above its own pads for `hover` of the flight, and
# everything left is a descent along the board normal -- perpendicular to the board, because
# that is the only direction still in the offset by then. See flight_world. In frames, for the
# three of them: 64 / 14 / 26, 62 / 13 / 25 and 82 / 16 / 38, so each hero floats for about
# half a second and takes 0.83 - 1.27 s to come down.
#
# `settle` is 0 for all three, and that is a consequence rather than an omission: the hop
# exists to sell a part being dropped, and a part that has just descended 22 - 62 mm under
# control has nothing to bounce off.
HERO_MOVES = (
    # `hover_at` 11 rather than 17: it reads as a part being *placed* only if the last gap is
    # small enough that the descent is a settle rather than a drop. Same 26 frames over 11 mm
    # instead of 17, so it comes down at 0.42 mm/frame against 0.65, and the ADC still floats
    # a third of a half-frame above its own pads while it hovers.
    ("adc", dict(travel=104, rise=26, sector=168, reach=1.30, arc=0.42, spin=54,
                 tumble=118, lift=0.20, settle=0.0, approach=0.62, hover=0.13,
                 hover_at=11)),
    ("driver", dict(travel=100, rise=22, sector=326, reach=1.45, arc=0.26, spin=-38,
                    tumble=58, lift=0.12, settle=0.0, approach=0.62, hover=0.13,
                    hover_at=14)),
    ("mcu", dict(travel=136, rise=34, sector=96, reach=1.70, arc=0.55, spin=74,
                 tumble=46, lift=0.26, settle=0.0, approach=0.60, hover=0.12,
                 hover_at=16)),
)

# Subject names in TARGET_BEATS that are wave groups rather than heroes: the aim goes to the
# group's own centre. Only the connector needs one -- it is the one part the camera path
# cannot present on its own.
#
# Not aimed *at* it, though: `bias` pulls the aim back towards the board centre and `nudge`
# offsets it in board millimetres, and both are composition rather than geometry.
#
#   bias 0.78   aimed dead centre, the connector fills the middle of the frame and the third
#               of it beyond is bare backdrop -- the part sits on the board's east edge with
#               nothing past it. At 0.78 it lands on the right third with the board filling
#               the rest, and the aim's excursion is a fifth shorter, which is what keeps the
#               two handoffs it adds in the same family as the hero traverses instead of the
#               fastest moves in the piece (flow 4.7 and 5.3 x median at 1.00, 3.8 and 4.8 at
#               0.78, against 4.2 for adc -> driver).
#   nudge -16   the connector is 94 mm long, it runs along the board's north-south axis, and
#               `orb` is within 15 deg of that axis while it lands -- so it is nearly end-on,
#               and perspective puts its screen centre well below its geometric one. Aimed at
#               the centre, the near end hung 0.27 of a half-frame under the bottom edge.
#               The frame cannot simply be opened instead: `width` is 135 mm here against a
#               94 mm part, and CAM_BEATS is not this fix's to touch. Measured, not guessed,
#               and it is a *bounded* fix rather than a comfortable one: -16 mm is what puts
#               the whole silhouette in frame at the landing with nothing to spare, and -20,
#               which would give it real margin, turns the aim's own travel through 121 deg
#               at f1478 -- a direction reversal, which is the one thing the camera rework
#               spent itself on removing. So the margin is what was given up, not the rule.
SUBJECT_GROUPS = ("harting",)
SUBJECT_AIM = {"harting": dict(bias=0.78, nudge=(0.0, -16.0))}

# Amplitude of the hover float, in mm: (along the board normal, across it). Periods are 1.6 s
# and 2.3 s -- incommensurate, so the pair never repeats inside a hover. Small on purpose: at a
# hero close-up 0.5 mm is 5 px of a 960-wide frame and 12 of a 2560, which reads as a part being
# held rather than as a part moving. See flight_world.
FLOAT_MM = (0.5, 0.35)

# Entry sectors for the supporting sub-waves, cycled so consecutive sub-waves never come
# from the same side. The two foreground values are offset from a dead-on 270 so a swarm
# never flies straight down the lens.
SECTORS = (4, 184, 62, 236, 128, 310, 168, 22)

# How far outside the frame a part has to start, as a fraction of the half-frame, and how the
# solve gets there. See entry_basis: `reach` is authored per wave and then grown until the
# part's own silhouette is off screen on the frame it appears, which is the only form of the
# requirement that survives a 94 mm connector and a 1 x 0.5 mm 0402 in the same table.
ENTRY_PAD = 0.06
ENTRY_GROW = 1.05
ENTRY_TRIES = 48

# ------------------------------------------------------------------------------- camera
#
# Beats, not frames-of-animation: everything between them is a natural cubic spline, which
# is C2, so the camera crosses a beat with no visible kick in speed. The last beat's frame
# is the end of the piece.
#
#   orb     the camera's azimuth *in the board's own yaw frame*, in degrees, and the one
#           channel that has to be monotone. Every board feature's screen position depends
#           on it; the world frame only holds the lights. It runs -437 to -77 here: one
#           continuous 360 deg lap around the board, ending exactly where it started.
#   el      elevation, degrees, unaffected by the board's yaw. One arc for the whole piece
#           -- 7 deg grazing on the copper, up to 35 over the hero landings, easing back to
#           27. Roll is the board's job (see RIG_BEATS): the underside is shown by turning
#           the board over, not by dipping the camera under the board plane, which is what
#           v2 did and what cost it a reversal in elevation at f204.
#   width   horizontal field at the target, in mm. This sets the distance, because how much
#           of the board the frame spans is what actually decides readability. It has
#           exactly one minimum in the piece, at f1880: everything before it is one
#           continuous approach and everything after is one continuous retreat, so there is
#           no frame at which the framing changes its mind.
#   fstop   restrained, and the numbers are computed rather than chosen for feel. Depth of
#           field is 2*N*c*(1+m)/m^2 with m = 36/width, so at width 46 mm f/7.1 gives ~1 mm
#           of depth: the first probe pass turned every landed part 20 mm from the ADC into
#           a bokeh blob. Hero close-ups therefore sit at width 62-70 mm and f/13-f/16
#           (4-6 mm), fabrication and the swarm at f/18-f/20 (15-24 mm, which covers the
#           whole board surface), and the finale at f/14. There is still a visible falloff
#           behind the subject; there is no longer a shot where most of the board is soft.
#   light   rides the whole calibrated rig; fillx/rimx additionally narrow the lighting
#           onto a hero landing by pulling the fill down and the rim up.
#
# Every column is two or three monotone arcs, and their turning points are deliberately *not*
# at the same frames: width crests at f610 and bottoms out at f1880, elevation crests at
# f1790, fstop at f707, light bottoms at f1911, and the subject hands over at the frames in
# TARGET_BEATS. What made v2 read as separate shots was not that any one channel was rough --
# all of them were C2 -- but that they all changed at once, seven times, at the seven subject
# changes. A move the eye can follow only ever has one thing arriving at a time.
#
# Counts, from tools/camera_flow.py: orb 0 direction changes, lens 0, roll 0, el 1, width 2.
# fstop, light, fillx and rimx report a handful more, all of them sub-perceptual ripple from
# re-interpolating these samples with a natural cubic -- the largest is 0.0035 of an f-stop
# and 0.6 % of a fill multiplier. Nothing there is geometry.
#
# The numbers are generated rather than typed: `orb` is the integral of a smooth deg/s
# profile, which makes monotonicity structural, and the value columns are sampled off a
# monotone cubic through control points so no segment overshoots. Retiming means editing
# that profile and re-sampling -- and then checking it with tools/camera_flow.py, which
# measures the screen motion this table produces rather than whether its curves are smooth.
CAM_BEATS = (
    #  f      orb     el  width  lens fstop light fillx  rimx   roll
    # The copper opening measures mean luma 0.06 at light 1.00 -- correct for a dark studio
    # with an unlit board, but 40 % of the frame crushed to black. Lifted, not reframed: the
    # grazing angle and the thickness in shot are the point of the beat. orb -437 is the
    # finale's own angle less one full lap, so the piece opens and closes on the same view of
    # the board with a complete orbit in between.
    (1,     -437.0,  7.0, 126.0,  74.0, 17.0, 1.22, 1.00, 1.00, -2.80),
    (90,    -420.9,  9.8, 138.0,  74.8, 17.4, 1.19, 1.00, 1.02, -2.69),
    (170,   -406.0, 12.4, 151.0,  75.5, 17.7, 1.15, 1.01, 1.03, -2.58),
    (250,   -390.8, 15.3, 159.0,  76.2, 18.0, 1.11, 1.01, 1.05, -2.48),
    (330,   -375.2, 17.8, 165.0,  77.0, 18.3, 1.07, 1.02, 1.08, -2.38),
    (400,   -361.3, 19.2, 170.0,  77.7, 18.6, 1.04, 1.02, 1.10, -2.29),
    (470,   -346.9, 20.5, 174.0,  78.5, 18.8, 1.02, 1.03, 1.12, -2.20),
    # Widest in the piece, and the only maximum `width` has: the two mask films need room to
    # arrive from opposite sides at once, and the board is edge-on while they do it.
    # Everything after this beat is one continuous approach, 1350 frames of it.
    (540,   -332.0, 22.7, 176.0,  79.3, 18.9, 1.00, 1.03, 1.13, -2.10),
    (610,   -316.2, 25.0, 176.5,  80.0, 19.1, 0.99, 1.04, 1.14, -2.00),
    (680,   -299.2, 26.6, 175.5,  80.6, 19.2, 0.98, 1.04, 1.15, -1.89),
    (750,   -280.9, 28.0, 173.5,  81.1, 19.2, 0.97, 1.05, 1.15, -1.78),
    (820,   -261.1, 29.3, 171.5,  81.5, 19.2, 0.96, 1.06, 1.15, -1.67),
    (890,   -239.7, 30.2, 169.0,  82.0, 19.2, 0.95, 1.06, 1.15, -1.55),
    (960,   -216.6, 30.7, 166.5,  82.5, 19.2, 0.94, 1.06, 1.15, -1.42),
    (1030,  -191.6, 31.1, 164.0,  82.9, 19.2, 0.94, 1.07, 1.16, -1.29),
    (1100,  -164.8, 31.4, 161.0,  83.4, 19.2, 0.94, 1.07, 1.16, -1.16),
    (1180,  -131.7, 31.7, 157.5,  84.0, 19.1, 0.93, 1.08, 1.16, -1.00),
    (1260,   -96.9, 32.1, 153.5,  84.6, 19.0, 0.93, 1.09, 1.17, -0.83),
    (1340,   -61.0, 32.4, 149.0,  85.3, 18.9, 0.92, 1.09, 1.17, -0.66),
    (1420,   -24.4, 32.8, 144.0,  86.1, 18.7, 0.91, 1.10, 1.19, -0.47),
    # The approach steepens through here -- 2.5 %/s of width at f1500, 5.1 %/s by f1760 --
    # while the subject is already moving from the swarm to the ADC's pads, which
    # TARGET_BEATS starts at f1480. The tightening and the subject change overlap on purpose
    # and neither begins where the other does.
    (1500,    11.5, 33.2, 138.0,  87.0, 18.5, 0.90, 1.11, 1.20, -0.28),
    (1570,    41.4, 33.7, 130.0,  88.2, 18.3, 0.88, 1.12, 1.22, -0.11),
    (1640,    69.6, 34.4, 119.0,  89.6, 18.0, 0.86, 1.14, 1.24,  0.07),
    (1700,    92.2, 35.0, 107.0,  90.9, 17.6, 0.83, 1.15, 1.26,  0.24),
    (1760,   113.1, 35.3,  96.0,  92.0, 17.2, 0.81, 1.16, 1.28,  0.40),
    (1820,   132.5, 35.3,  88.0,  92.9, 16.9, 0.79, 1.17, 1.31,  0.57),
    # The closest the camera gets, 32 frames before the driver lands, and the one minimum in
    # `width`. There is no second push and no pull-back between the heroes: the ADC and the
    # driver are 38 mm apart on the board, so the camera simply travels from one to the other
    # at this width, and the Teensy's landing is covered by a retreat that has already begun.
    (1880,   150.4, 35.0,  84.0,  93.6, 16.6, 0.78, 1.18, 1.34,  0.75),
    (1940,   167.0, 34.5,  85.0,  94.3, 16.4, 0.78, 1.18, 1.37,  0.94),
    (2000,   182.7, 33.8,  90.0,  95.0, 16.2, 0.79, 1.17, 1.40,  1.14),
    (2060,   197.5, 33.0, 100.0,  95.6, 16.0, 0.81, 1.16, 1.43,  1.34),
    (2120,   211.6, 32.2, 116.0,  96.2, 15.8, 0.84, 1.15, 1.45,  1.55),
    # The Teensy lands on f2140 at width ~122 -- a 61 mm module across half the frame, with
    # the retreat running through it at 7 %/s and never pausing for the landing. The old
    # table pulled 92 -> 196 mm in 32 frames to catch this same moment: 94 %/s, and the worst
    # single lurch in the piece.
    (2180,   224.9, 31.3, 134.0,  96.8, 15.5, 0.87, 1.13, 1.48,  1.76),
    (2250,   239.3, 30.2, 154.0,  97.5, 15.0, 0.90, 1.11, 1.50,  2.00),
    # The finale is the last 380 frames of that same retreat rather than a shot of its own:
    # width keeps opening, elevation keeps easing down, the orbit keeps turning at 2.6 deg/s
    # decaying to 1.2, and the aim drifts off the Teensy back to the board centre across all
    # of it while the narrow sweep rakes the length of the metal. Widths come from
    # frame_coverage, not from eye -- the assembly spans 165 mm and its projected diagonal is
    # 192, and a falling elevation shrinks its vertical extent as the frame opens. It read
    # 238 while the parenting bug had the assembly spanning 252 mm instead of 165: a framing
    # number tuned against a broken scene encodes the breakage. Light rides back *up* here,
    # because the hero section held the mask 20 % under and deep purple is the whole point of
    # the chosen variant.
    (2320,   252.3, 29.2, 173.0,  98.2, 14.6, 0.92, 1.09, 1.50,  2.25),
    (2390,   264.1, 28.3, 190.0,  98.8, 14.2, 0.94, 1.07, 1.44,  2.51),
    (2455,   274.0, 27.4, 205.0,  99.4, 13.8, 0.95, 1.06, 1.36,  2.76),
    # Not a freeze. The table is still moving on the last frame -- 1.2 deg/s of orbit and
    # 2.7 % of width per second -- because v2 spent its final 5.4 s under a third of its own
    # median screen motion, and a shot that stops before it ends reads as one that ended early.
    (2520,   283.0, 26.6, 216.0, 100.0, 13.5, 0.96, 1.05, 1.30,  3.00),
)
CAM_CHANNELS = ("orb", "el", "width", "lens", "fstop", "light", "fillx", "rimx", "roll")

# The subject track, and deliberately its own table -- Camera.target says why it cannot be a
# column of CAM_BEATS. A crossfade runs for the whole gap between two entries, so a repeated
# name is a hold and the gap after it is the handoff. Every one of these is long, and every
# one begins before the moment it is leaving has finished:
#
#   1400 -> 1515  the aim leaves the swarm 58 frames before the last *supporting* part lands
#                 and arrives on the connector 9 frames before it does
#   1580 -> 1700  leaves the connector 56 frames after that landing and reaches the ADC's
#                 pads 20 frames before the ADC does, so the camera is waiting at the
#                 destination rather than chasing the part into it
#   1790 -> 1900  leaves the ADC 70 frames after that landing, crosses the 38 mm to the
#                 driver, arrives 12 frames early
#   1975 -> 2115  the same again over the 67 mm to the Teensy, arriving 25 frames early
#   2200 -> 2520  then one 10.7 s drift off the Teensy back to the board centre, which is the
#                 entire finale
#
# v2's seven handoffs averaged 1.2 s and every one of them landed on top of a zoom. These
# average 5.4 s and none of them shares a frame with a turning point in any other column.
#
# `harting` is the one addition draft 3 makes to this table, and it is here because the
# Harting is the only part on the board the camera could not show: it sits 75 mm off centre at
# the board's east end, the frame is 135-145 mm wide by the time it lands, and the aim was on
# the swarm 60 mm the other way -- so the biggest connector on the board arrived with its
# centre 1.12 frame-widths off screen, clipped into the bottom-right corner. Nothing about the
# camera path is wrong there and none of it is touched: `width` still has its one minimum at
# f1880 and `orb` is still monotone. What was missing is that the subject track never named
# the part. The excursion out to the east end and back to the ADC is a reversal in the aim's
# own travel, which is what the swarm damping exists to avoid -- so it is spent deliberately,
# on one part, over 3.8 s out and 4.0 s back, and camera_flow.py is what says it costs
# nothing: still 0 direction reversals, and the two new handoffs report less flow and less
# lurch than the single swarm -> adc handoff they replace.
TARGET_BEATS = (
    (1, "board"), (150, "board"), (330, "etch"), (560, "etch"), (700, "board"),
    (1060, "board"), (1240, "swarm"), (1400, "swarm"), (1515, "harting"), (1580, "harting"),
    (1700, "adc"), (1790, "adc"), (1900, "driver"), (1975, "driver"), (2115, "mcu"),
    (2200, "mcu"), (2520, "board"),
)

# The board's own move, in the same C2 spline: yaw, then roll.
#
# Yaw is now nearly invisible on its own. `orb` is board-relative, so the camera carries the
# board's yaw with it and what yaw actually controls is *the lighting* -- how fast the four
# fixed studio sources rake across the copper, and where the key sits relative to the face
# being presented. It runs -22 to 456 deg, monotone, peaking at 11.1 deg/s against v2's
# 38.6: with SHUTTER at 0.12 that is 40 % less smear on a 0.25 mm trace than the frames the
# shutter number was chosen against.
#
# Roll does the whole bottom-copper reveal, which v2 split between a -52 deg roll and a dip
# to camera elevation -17. Splitting it was what put a reversal in the middle of the
# elevation arc, and the reason given for splitting it -- that 105 deg of roll means
# 45 deg/s -- was a consequence of the 39 s runtime, not of the shot. Over 84 s the same
# turn-over is 22 deg/s at its fastest, and the camera never has to leave its arc.
#
# The roll profile is checked against `board_facing`, not eyeballed: +0.39 to +0.44 across
# the top etch (top face presented) and -0.35 to -0.48 across the bottom etch (underside
# presented, which is what the check asks for).
#
# The films used to be timed to arrive at facing ~0, on the reasoning that dead edge-on is
# the one attitude in which both of them read as approaching from opposite sides at once.
# The probe frames say otherwise: at facing -0.07 the board is a bright line one pixel wide
# and there is nothing on screen for a film to land on. They now touch at +0.16 and +0.26,
# with the board on its way back up -- the top film comes down onto a visible face and the
# bottom one still reads, in silhouette, against the backdrop below the edge.
RIG_BEATS = (
    (1, -22.0, 20.0), (90, -15.7, 18.6), (170, -9.6, 17.0), (250, -3.0, 13.0),
    # The turn-over. 56 deg over 180 frames, which peaks at 13 deg/s -- and the depth
    # of it comes from board_facing, not from feel: -45 is what puts the underside at
    # -0.41, past the -0.35 the check asks for, where going on to -56 for its own sake
    # cost 20.7 deg/s of board rotation across routing that had just been etched.
    (290, 0.6, 10.0), (330, 4.5, 4.0), (380, 9.7, -13.0), (430, 15.5, -35.0),
    (470, 20.4, -50.0), (520, 27.1, -53.0), (560, 33.0, -46.0), (580, 35.7, -40.0), (650, 46.7, -12.0),
    (720, 58.6, -5.0), (800, 73.4, -2.4), (890, 91.8, -1.2),
    # The energetic stretch, and it is the *lights* that move: 196 deg between f890 and
    # f1500 while the supporting waves land, peaking at 11.1 deg/s. v2 peaked at 38.6.
    (1030, 126.5, -1.8), (1180, 173.7, -1.0), (1340, 232.0, -0.6), (1500, 287.6, -0.3),
    (1640, 330.4, -0.2), (1760, 361.8, -0.1), (1880, 388.4, -0.1), (2000, 410.6, 0.0),
    # Decelerating through the finale -- 3.6, 2.2, 1.1 and finally 0.45 deg/s -- so the
    # board never stops but has clearly come to rest.
    (2120, 428.5, 0.0), (2250, 442.8, 0.0), (2390, 452.2, 0.0), (2520, 456.0, 0.0),
)

# The fifth light: a narrow strip that rides with the board, so a controlled highlight can
# be walked along the etch front, narrowed onto a hero landing, and swept across the metal
# in the finale. `at` names a hero whose position supplies px/py; otherwise px/py are board
# millimetres from the board centre. pz is signed, so a negative one lights the underside.
#   f      e     px    py   pz    sx    sy   at
SWEEP_BEATS = (
    (1,    0.00, -95,   0,   46,  150,   9, None),
    (170,  0.55, -90,   0,   42,  150,   9, None),
    (330,  0.55,  90,   0,   42,  150,   9, None),
    (360,  0.05,  96,   0,    0,  150,   9, None),
    (425,  0.70,  88,   0,  -40,  150,   9, None),
    (545,  0.70, -92,   0,  -40,  150,   9, None),
    (580,  0.00, -96,   0,   46,  150,   9, None),
    (664,  0.60, -90,   0,   52,  130,  14, None),
    (846,  0.60,  90,   0,   52,  130,  14, None),
    # The strip stays dark through the swarm: the board is yawing at up to 11 deg/s there, so
    # the four studio sources are already raking it, and a fifth travelling highlight only
    # competes. These three rows also *condition the spline*, which matters more than it looks:
    # a natural cubic dropping 0.60 in 34 frames and then running flat for 720 undershoots to
    # -0.63 after the knot, max(0, e) clamps that flat, and the sweep came up 350 frames late.
    (900,  0.18,  40,   0,   58,  130,  14, None),
    (980,  0.00,   0,   0,   64,  120,  13, None),
    (1240, 0.00,   0,   0,   58,  110,  12, None),
    # px/py on an `at` row are placeholders: bake_lights substitutes the named hero's board
    # position into the table before splining, so the strip travels between the three of them
    # instead of jumping. The row between the driver and the Teensy sits at px 0 — on the path
    # from -36.4 to +27 — so that travel does not double back on itself either.
    (1600, 0.90,   0,   0,   26,   26,  10, "adc"),
    # Holds the ADC level for its landing, and stops `e` overshooting to 0.99 on the way past
    # 0.90 — a long rise into a knot rings after it, and this is the hero close-up.
    (1700, 0.90,   0,   0,   25,   26,  10, "adc"),
    (1800, 0.85,   0,   0,   24,   26,  10, "driver"),
    (1930, 0.30,   0,   0,   50,   60,  14, None),
    (1990, 0.70,   0,   0,   34,   50,  12, "mcu"),
    (2120, 0.70,   0,   0,   30,   50,  12, "mcu"),
    # The finale rake, and the reason the ending is worth the extra frames. It repositions
    # dark -- e drops to 0.10 while it travels out to the far end -- and then makes one
    # continuous pass back along the board. px is monotone from f2200 to the last frame, so
    # there is no reposition flash: it gets narrower, closer and brighter as it crosses the
    # Harting pin field (local x +77), then the Teensy and its USB shell (+27), then the
    # trimmers and the power section. 10.7 s, exactly as long as the camera's own retreat.
    (2160, 0.10,  78,   0,   40,   90,   6, None),
    (2200, 0.58,  92,   0,   42,  120,   5, None),
    (2290, 0.66,  60,   0,   36,  116,   4, None),
    (2380, 0.62,  24,   3,   32,  110,   4, None),
    (2460, 0.54, -14,   7,   32,  104,   5, None),
    (2520, 0.46, -40,  10,   36,  100,   5, None),
)
SWEEP_CHANNELS = ("e", "px", "py", "pz", "sx", "sy")
SWEEP_BASE_WATTS = 0.95

# UNDER: a broad box below the board, energy only. All four studio lights are above the
# board, so while the underside is the subject -- the bottom etch, and the bottom film
# arriving -- bare copper down there is a black mirror and the shot is dead. On for exactly
# that window and off either side of it.
#   f     e
UNDER_BEATS = ((1, 0.00), (370, 0.00), (425, 1.55), (545, 1.55), (590, 1.35),
               (640, 1.00), (700, 0.50), (770, 0.12), (830, 0.00), (2520, 0.00))
UNDER_BASE_WATTS = 1.35


# ---------------------------------------------------------------------------------- math


def smootherstep(t: float) -> float:
    """C2-continuous ease. Its second derivative vanishes at both ends, so crossing it has
    no visible kick in speed -- which plain smoothstep does have."""
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


class Spline:
    """Natural cubic spline through (x, y), clamped to the end values outside the range.

    C2 by construction, which is what the camera needs: a beat table interpolated with
    per-segment easing has a discontinuous second derivative at every beat, and over a long
    move that reads as the operator nudging the head. Natural (zero curvature at the ends)
    rather than clamped, because the tables carry no tangents.
    """

    def __init__(self, xs, ys):
        self.xs = [float(v) for v in xs]
        self.ys = [float(v) for v in ys]
        n = len(self.xs)
        self.c2 = [0.0] * n
        if n < 3:
            return
        h = [self.xs[i + 1] - self.xs[i] for i in range(n - 1)]
        alpha = [0.0] * n
        for i in range(1, n - 1):
            alpha[i] = (3.0 * (self.ys[i + 1] - self.ys[i]) / h[i]
                        - 3.0 * (self.ys[i] - self.ys[i - 1]) / h[i - 1])
        lo, mu, z = [1.0] + [0.0] * (n - 1), [0.0] * n, [0.0] * n
        for i in range(1, n - 1):
            lo[i] = 2.0 * (self.xs[i + 1] - self.xs[i - 1]) - h[i - 1] * mu[i - 1]
            mu[i] = h[i] / lo[i]
            z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / lo[i]
        for i in range(n - 2, -1, -1):
            self.c2[i] = z[i] - mu[i] * self.c2[i + 1]

    def __call__(self, x: float) -> float:
        xs, ys = self.xs, self.ys
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        # Hermite form of the cubic, written from the second derivatives.
        return (ys[i] * (1 - t) + ys[i + 1] * t
                + ((1 - t) ** 3 - (1 - t)) * self.c2[i] * h * h / 6.0
                + (t ** 3 - t) * self.c2[i + 1] * h * h / 6.0)


def orbit_dir(az_deg: float, el_deg: float) -> Vector:
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el),
                   math.sin(el)))


def hex2lin(value: str) -> tuple[float, float, float]:
    """sRGB hex -> linear Rec.709, because Blender colour sockets are linear."""
    out = []
    for i in (0, 2, 4):
        c = int(value[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def axis_range(phi_deg: float, size_mm) -> tuple[float, float]:
    """The span of s = u*W*cos(phi) + v*H*sin(phi) over the unit UV square, in mm."""
    w, h = size_mm
    a, b = w * math.cos(math.radians(phi_deg)), h * math.sin(math.radians(phi_deg))
    return min(0.0, a) + min(0.0, b), max(0.0, a) + max(0.0, b)


def front_travel(phi_deg: float, size_mm, margin: float = 0.10) -> tuple[float, float]:
    """The span of `s` over which front_point actually moves.

    front_point clamps u and v inside the outline, so past a certain s the aim stops dead
    while the front carries on -- a corner in the aim's *velocity*, and the largest single
    lurch tools/camera_flow.py found anywhere in the first cut of this table (117x the
    median rate of change, at f310, right at the end of the top etch). Ramping the aim
    across this span instead means the clamp is only ever reached at zero velocity.
    """
    w, h = size_mm
    phi = math.radians(phi_deg)
    gx, gy = w * math.cos(phi), h * math.sin(phi)
    g2 = gx * gx + gy * gy
    s_centre = 0.5 * (gx + gy)
    lo, hi = -1e9, 1e9
    for g in (gx, gy):
        if abs(g) < 1e-9:      # this axis never leaves the middle, so it never clamps
            continue
        a = s_centre + (margin - 0.5) * g2 / g
        b = s_centre + (0.5 - margin) * g2 / g
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
    return lo, hi


def front_point(s: float, phi_deg: float, size_mm) -> Vector:
    """A point on the front line s = const, in board-local metres.

    The front is a line in UV, and UV is a linear map of board XY over the layer bounds, so
    the closest point on that line to the board centre is where to aim: it is on the board,
    it tracks the front, and it needs no search. Clamped inside the outline so a parked
    front cannot pull the focus off the board.
    """
    w, h = size_mm
    phi = math.radians(phi_deg)
    gx, gy = w * math.cos(phi), h * math.sin(phi)
    g2 = gx * gx + gy * gy
    s_centre = 0.5 * (gx + gy)
    u = min(0.92, max(0.08, 0.5 + (s - s_centre) * gx / g2))
    v = min(0.92, max(0.08, 0.5 + (s - s_centre) * gy / g2))
    return Vector(((u - 0.5) * w / 1000.0, (v - 0.5) * h / 1000.0, 0.004))


# ----------------------------------------------------------------- board <-> scene join
#
# Unchanged in substance from v1: these are what make "the ADC" a fact about the board
# rather than a guess about the scene, and a failure here stops the render.


def model_stem(obj, known) -> str:
    """The 3D-model filename this object was imported from.

    Read off the *mesh*, not the object. Instances of one model share its mesh datablock,
    which keeps the filename intact, while object names are mangled two ways: Blender
    truncates a name to make room for its `.001` suffix, and it *replaces* a trailing
    numeric-looking suffix, which turns a second `IND-SMD_L6.0-W6.0-H4.5` into
    `IND-SMD_L6.0-W6.0-H4.001`.
    """
    name = re.sub(r"\.\d{3}$", "", obj.data.name)
    if name in known:
        return name
    hits = [k for k in known if k.startswith(name)]
    return hits[0] if len(hits) == 1 else name


def recover_offset(components, parts) -> Vector:
    """Find the board-centring offset by vote instead of assuming it.

    Every (object, footprint) pair votes for the offset it would imply; the true offset is
    the one ~100 parts agree on, then averaged over its own voters for precision.
    """
    exp = [(p["x"], -p["y"]) for p in parts for _ in p["models"]]
    obs = [(o.matrix_world.translation.x * 1000.0, o.matrix_world.translation.y * 1000.0)
           for o in components]
    votes = {}
    for ox, oy in obs:
        for ex, ey in exp:
            votes.setdefault((round((ox - ex) / 0.5), round((oy - ey) / 0.5)), []).append(
                (ox - ex, oy - ey))
    winners = votes[max(votes, key=lambda k: len(votes[k]))]
    offset = Vector((sum(v[0] for v in winners) / len(winners),
                     sum(v[1] for v in winners) / len(winners)))
    print(f"  centring offset {offset.x:+.3f}, {offset.y:+.3f} mm "
          f"({len(winners)}/{len(obs)} parts agree)")
    return offset


def match_objects(components, parts, offset_mm):
    """Assign every component object a designator, by position within its own model class.

    Restricting candidates to footprints that reference the same 3D model is what makes
    this exact rather than approximate: 29 C_0402 objects are matched against the 29 C_0402
    footprints and nothing else, so a 0.4 mm neighbour cannot steal a match.
    """
    wanted = {}
    for part in parts:
        for model in part["models"]:
            wanted.setdefault(model["file"], []).append(part)

    matched, worst, unmatched, counts = {}, (0.0, None), [], {}
    for obj in components:
        stem = model_stem(obj, wanted)
        cands = wanted.get(stem)
        if not cands:
            unmatched.append((obj.name, "no footprint uses this model"))
            continue
        here = Vector(obj.matrix_world.translation[:2]) * 1000.0 - offset_mm
        best = min(cands, key=lambda p: (p["x"] - here.x) ** 2 + (-p["y"] - here.y) ** 2)
        d = math.dist((best["x"], -best["y"]), (here.x, here.y))
        matched[obj.name] = best["ref"]
        counts[best["ref"]] = counts.get(best["ref"], 0) + 1
        # Position only has a job when a model class has more than one candidate. With a
        # single candidate the model name has already decided it, and a non-zero distance is
        # expected: a footprint's `(offset)` moves the object's origin off the footprint
        # origin -- 1.25 mm for J8's Harting, 31.7 mm for a model placed by its corner.
        if len(cands) > 1 and d > worst[0]:
            worst = (d, f'{obj.name} -> {best["ref"]}')

    for part in parts:  # every placed footprint collects exactly as many objects as models
        want, got = len(part["models"]), counts.get(part["ref"], 0)
        if got != want:
            unmatched.append((part["ref"], f"{got} objects, expected {want}"))

    print(f"  matched {len(matched)}/{len(components)} objects to {len(counts)} designators,"
          f" worst ambiguous-class residual {worst[0]:.3f} mm ({worst[1]})")
    if unmatched:
        for name, why in unmatched[:12]:
            print(f"    UNMATCHED {name}: {why}")
        sys.exit(f"component matching failed on {len(unmatched)} item(s)")
    return matched


def resolve_heroes(parts):
    found = {}
    for name, needle in HEROES:
        hits = [p for p in parts if needle.lower() in p["value"].lower()]
        if len(hits) != 1:
            sys.exit(f"hero '{name}': {len(hits)} parts match {needle!r} "
                     f"({[h['ref'] for h in hits]}) -- expected exactly one")
        found[name] = hits[0]["ref"]
    return found


# -------------------------------------------------------------------------- scheduling


def order_key_factory(parts):
    """A rotated sweep axis, so a sub-wave arrives as a diagonal band across the board
    rather than as a column marching sideways."""
    phi = math.radians(20)
    pos = {p["ref"]: (p["x"], -p["y"]) for p in parts}
    return pos, lambda ref: pos[ref][0] * math.cos(phi) + pos[ref][1] * math.sin(phi)


def group_parts(refs, parts, heroes, order_key):
    """Sort designators into hero, placement group, or unclassified."""
    part_of = {p["ref"]: p for p in parts}
    groups, seen = {}, set(heroes.values())
    for label, needles in GROUP_TESTS:
        picked = [r for r in refs if r not in seen
                  and any(n in part_of[r]["footprint"] for n in needles)]
        groups[label] = sorted(picked, key=order_key)
        seen.update(picked)

    # Anything the tests missed still has to be placed, or it would appear from nowhere at
    # frame 1. It goes in with `power`, and is named so the tests can be extended.
    leftover = sorted(set(refs) - seen, key=order_key)
    if leftover:
        print(f"  note: {len(leftover)} part(s) matched no group test, placed with 'power': "
              f"{', '.join(leftover)}")
        groups["power"] = sorted(groups.get("power", []) + leftover, key=order_key)
    return groups


def wave_schedule(groups, parts, order_key):
    """ref -> (start, land, sector, spec) for every supporting part, plus the sub-waves.

    A group is split into `sub` diagonal bands of equal size, so the bands are balanced and
    each is a region of the board; within a band, parts are sorted by package first, so a
    swarm reads as one kind of part arriving, then by position. Each band gets its own entry
    sector, cycling, so consecutive swarms never come from the same side of frame.
    """
    part_of = {p["ref"]: p for p in parts}
    plan, subwaves, sector_i = {}, [], 0
    for label, spec in WAVES:
        refs = groups.get(label) or []
        if not refs:
            continue
        n_sub = max(1, min(spec["sub"], len(refs)))
        bands = [b for b in (refs[i * len(refs) // n_sub:(i + 1) * len(refs) // n_sub]
                             for i in range(n_sub)) if b]
        for j, band in enumerate(bands):
            band = sorted(band, key=lambda r: (part_of[r]["footprint"], order_key(r)))
            sector = SECTORS[sector_i % len(SECTORS)]
            sector_i += 1
            # Sub-waves share the group's slot, each offset by its share of the span, and
            # each setting off over 80 % of that share -- so they read as separate arrivals
            # rather than one continuous drizzle.
            share = spec["span"] / len(bands)
            first = spec["start"] + share * j
            step = (share * 0.80) / max(1, len(band) - 1)
            for i, ref in enumerate(band):
                start = int(round(first + i * step))
                plan[ref] = (start, start + spec["travel"], sector, spec)
            subwaves.append((label, j, sector, band, int(round(first)),
                             int(round(first + share * 0.80)) + spec["travel"]))
    return plan, subwaves


def hero_schedule(after_waves):
    out, f = {}, after_waves
    for name, m in HERO_MOVES:
        start = f + F_HERO_GAP
        out[name] = (start, start + m["travel"], m)
        f = start + m["travel"]
    return out, f


# ---------------------------------------------------------------------- rig and camera


class Rig:
    """The board's own move, as an analytic function of frame.

    Everything else asks this where the board is: the camera for its follow term, the
    component solver for where a footprint will be at the frame a part has to land on it,
    and the sweep light for a board-local position. Deliberately not the depsgraph -- the
    solver needs frame 700 while the scene sits on frame 1.
    """

    def __init__(self, centre: Vector):
        self.centre = centre.copy()
        fs = [b[0] for b in RIG_BEATS]
        self.yaw = Spline(fs, [b[1] for b in RIG_BEATS])
        self.roll = Spline(fs, [b[2] for b in RIG_BEATS])

    def euler(self, frame: float) -> tuple[float, float]:
        return self.yaw(frame), self.roll(frame)

    def rotation(self, frame: float) -> Matrix:
        yaw, roll = self.euler(frame)
        # Blender's XYZ Euler order composes as Rz @ Ry @ Rx, so an euler of
        # (roll, 0, yaw) on the empty is exactly this matrix. Kept in step deliberately.
        return (Matrix.Rotation(math.radians(yaw), 4, "Z")
                @ Matrix.Rotation(math.radians(roll), 4, "X"))

    def matrix(self, frame: float) -> Matrix:
        return Matrix.Translation(self.centre) @ self.rotation(frame)

    def to_world(self, frame: float, local: Vector) -> Vector:
        """A point in board-local coordinates (origin at the board centre) -> world."""
        return self.matrix(frame) @ local

    def basis(self, frame: float, world: Matrix, pre: Matrix) -> Matrix:
        """The matrix_basis a descendant needs in order to sit at `world` on `frame`.

        matrix_world = rig.matrix(f) @ pre @ matrix_basis, solved for the basis. `pre` is the
        whole constant chain between the rig and this object -- for a component that includes
        the board's own transform, because the importer parents components to the board and
        that transform is what centres them.
        """
        return pre.inverted() @ self.matrix(frame).inverted() @ world


class Camera:
    """The camera move, evaluated per frame from CAM_BEATS and TARGET_BEATS.

    `orb` is board-relative, so the only thing that carries the camera into the world is the
    board's own yaw, applied here. That is the whole of the follow: there is no separately
    authored world azimuth and no fraction to blend between the two frames, because the
    difference between them was what the viewer was actually watching, and splitting it
    across two channels is what let it reverse six times without anything looking wrong in
    the table.
    """

    def __init__(self, rig: Rig, targets: dict, sensor_mm: float = 36.0):
        self.rig, self.targets, self.sensor = rig, targets, sensor_mm
        self.end = int(CAM_BEATS[-1][0])
        fs = [b[0] for b in CAM_BEATS]
        self.ch = {name: Spline(fs, [b[1 + i] for b in CAM_BEATS])
                   for i, name in enumerate(CAM_CHANNELS)}
        self.t_frames = [b[0] for b in TARGET_BEATS]
        self.t_names = [b[1] for b in TARGET_BEATS]
        # A name in the subject track with nothing behind it would otherwise fail 1500 frames
        # later, inside a per-frame lambda lookup, on whichever caller got there first.
        missing = sorted(set(self.t_names) - set(targets))
        if missing:
            sys.exit(f"TARGET_BEATS names {missing} with no aim point: "
                     f"have {sorted(targets)}")

    def target(self, frame: float) -> Vector:
        """World-space aim point.

        The two neighbouring subject beats' local targets are blended and *then*
        rig-transformed: blending in board-local space is what keeps the aim on the board
        while the board turns, where blending world points would cut a chord straight
        through it.

        The subject track is its own table rather than a column of CAM_BEATS, and that is
        the whole reason a handoff can be slow. Riding the camera beats made the crossfade
        exactly as long as the gap between two of them, so tightening the framing anywhere
        near a change of subject shortened the handoff as a side effect -- which is how v2
        ended up with seven subject changes averaging 1.2 s, every one of them landing on
        top of a zoom.
        """
        i = max(0, min(bisect.bisect_right(self.t_frames, frame) - 1,
                       len(self.t_frames) - 1))
        aim = self.targets[self.t_names[i]](frame)
        if i + 1 < len(self.t_frames):
            span = self.t_frames[i + 1] - self.t_frames[i]
            t = smootherstep((frame - self.t_frames[i]) / span)
            aim = aim.lerp(self.targets[self.t_names[i + 1]](frame), t)
        return self.rig.to_world(frame, aim)

    def state(self, frame: float) -> dict:
        v = {k: s(frame) for k, s in self.ch.items()}
        aim = self.target(frame)
        tan_h = (self.sensor * 0.5) / v["lens"]
        radius = (v["width"] / 2000.0) / tan_h
        # `orb` is board-relative, so the board's yaw is what carries it into the world.
        direction = (Matrix.Rotation(math.radians(self.rig.yaw(frame)), 4, "Z")
                     @ orbit_dir(v["orb"], v["el"]))
        loc = aim + direction * radius
        # A drift that never quite stops: three incommensurate sines at ~0.2 % of the
        # working distance. Invisible frame to frame, and the reason the last second of the
        # piece is not frozen.
        drift = Vector((math.sin(frame * 0.0131), math.cos(frame * 0.0097),
                        math.sin(frame * 0.0071) * 0.6)) * (radius * 0.0022)
        loc = loc + drift
        quat = (aim - loc).to_track_quat("-Z", "Y") @ Quaternion(
            (0, 0, 1), math.radians(v["roll"]))
        v.update(loc=loc, quat=quat, aim=aim, radius=radius, tan_h=tan_h)
        return v


def frame_coverage(cam: Camera, rig: Rig, frame: int, hull_local, aspect: float):
    """How much of the frame the assembly fills, as (horizontal, vertical) fractions.

    1.0 means a point sits exactly on the frame edge, so anything above 1.0 is clipped. A
    hero composition wants ~0.9: an eyeballed `width` cannot be trusted here, because at a
    working distance of only ~3.4 board-lengths the near end of a tilted board projects
    considerably larger than the far end, and the first pass duly cropped the Harting.
    """
    st = cam.state(frame)
    to_cam = Matrix.LocRotScale(st["loc"], st["quat"], None).inverted()
    tan_h = st["tan_h"]
    tan_v = tan_h / aspect
    worst_h = worst_v = 0.0
    for point in hull_local:
        c = to_cam @ rig.to_world(frame, point)
        depth = -c.z
        if depth <= 1e-6:
            return 9.99, 9.99         # behind the camera
        worst_h = max(worst_h, abs(c.x) / (depth * tan_h))
        worst_v = max(worst_v, abs(c.y) / (depth * tan_v))
    return worst_h, worst_v


def board_facing(rig: Rig, st: dict, frame: float) -> float:
    """+1 when the board's top face is square to the camera, -1 when the bottom is.

    Printed by --plan-only, because "roll the board until the underside comes round" is not
    something to eyeball from a column of Euler angles: the camera's elevation and its
    follow term both change what a given roll actually shows.
    """
    normal = rig.rotation(frame).to_3x3() @ Vector((0, 0, 1))
    return normal.dot((st["loc"] - st["aim"]).normalized())


# ---------------------------------------------------------------------- component flight


def flight_world(rig: Rig, entry: dict, land_basis: Matrix, pre: Matrix,
                 centroid_local: Vector, frame: int, start: int, land: int, spec: dict,
                 jitter: tuple) -> Matrix:
    """Where one logical part is, in the world, on `frame`.

    Built as an offset from where its pads *currently* are, so a part chases a moving
    footprint and arrives on it exactly:

        W(f) = T(offset) . R_correct . rig(f) . P . L

    The lateral offset is large at the start and gone by u = 0.86; the height above the pads
    outlives it, so the last stretch is a short descent along the board normal. That
    ordering is the whole reason it reads as placement and not as a part being dragged into
    position. `entry` is the camera's basis at the entry frame, computed once per part.

    A part carrying `approach` splits that overlap into three phases instead of blending
    them, which is what the three hero landings want: the whole approach -- lateral, arc and
    orientation -- finishes at u = `approach`, the part then holds still above its own pads
    for `hover` of the flight, and the rest is a descent along the board normal alone. The
    first draft ran the lateral and the height decays concurrently for a hero too, and 104
    frames of two overlapping eases read as one continuous swoop with no moment of arrival
    in it. The cost is a faster approach, since the same distance is covered in 62 % of the
    frames -- measured, peak screen speed 0.47 -> 0.52 frame-widths/s for the ADC, against 1.45
    for the fastest supporting part, so there is room for it.
    """
    u = min(1.0, max(0.0, (frame - start) / max(1, land - start)))
    approach = spec.get("approach")
    if approach:
        q = min(1.0, u / approach)                 # the approach, on its own clock
        drop = min(0.98, approach + spec.get("hover", 0.0))
        a = smootherstep(q)                        # lateral gone at u = approach
        # Zero until the hover is over, so the height across it is *exactly* `hover_at`: a
        # hover that is still creeping downwards is not a hover.
        b = smootherstep((u - drop) / (1.0 - drop))
        r = smootherstep(q / 0.92)                 # square to its footprint before it hovers
    else:
        q = u
        a = smootherstep(u / 0.86)                     # lateral decay
        b = smootherstep(max(0.0, (u - 0.12) / 0.88))  # height decay, one beat behind
        r = smootherstep(u / 0.80)                     # orientation correction, done earlier

    world_land = rig.matrix(frame) @ pre @ land_basis
    centre_w = rig.to_world(frame, centroid_local)
    normal = (rig.rotation(frame).to_3x3() @ Vector((0, 0, 1))).normalized()
    lateral = entry["lateral"]
    perp = lateral.cross(normal)
    perp = perp.normalized() if perp.length > 1e-6 else entry["right"]

    # On the approach clock too: the bulge and the mid-flight lift are part of the flight in,
    # so both are gone by the time a hover starts. Left on `u` they would still be at 52 % of
    # their peak at u = 0.62, and the part would hover beside its pads rather than over them.
    arc = math.sin(math.pi * q) * (1.0 - q) ** 0.6
    rise = spec["rise"] * (1.0 + jitter[2]) / 1000.0
    settle = spec.get("settle", 0.0) / 1000.0
    hop = 0.0
    if settle and u > 0.86:
        s = (u - 0.86) / 0.14
        hop = settle * max(0.0, math.sin(2 * math.pi * s)) * (1.0 - s)

    # The height the part holds while it hovers, which is not the height it flew in at: those
    # were one number in the first cut of this and the hover then happened *above the top of
    # the frame*. A hero flies in 24 - 40 mm up because that is what clears the parts already
    # on the board, and the frame is 47 - 76 mm tall at a hero close-up, so holding the flight
    # height put the ADC at v 1.21 and the Teensy at 2.05 -- both out of shot, both then
    # dropping into frame from above. The excess over `hover` is given back over the approach,
    # so the part arrives at the height it is going to hold.
    hover_h = spec.get("hover_at", spec["rise"]) * (1.0 + jitter[2]) / 1000.0
    air = hover_h + (rise - hover_h) * (1.0 - a)
    # A hover is not a freeze. Two slow incommensurate sines -- one along the board normal, one
    # across it -- at a few tenths of a millimetre, so a part waiting over its pads reads as
    # held in air rather than parked in space. `a * (1 - b)` is the envelope and costs nothing
    # extra: it is zero through the fast part of the approach, exactly 1 across the hover, and
    # back to zero by the land frame, so the landing cannot inherit a wobble. Phase comes from
    # the part's own jitter, so no two heroes bob together.
    float_env = a * (1.0 - b) if approach else 0.0
    bob = FLOAT_MM[0] / 1000.0 * math.sin(frame * 0.130 + jitter[0])
    sway = FLOAT_MM[1] / 1000.0 * math.sin(frame * 0.091 + jitter[0] * 1.7)
    offset = (lateral * (entry["reach"] * (1.0 - a))
              + perp * (entry["half_w"] * spec["arc"] * arc + sway * float_env)
              + normal * (air * (1.0 - b) + rise * spec["lift"] * arc + hop
                          + bob * float_env))

    amount = 1.0 - r
    spin = Quaternion(normal, math.radians(spec["spin"] * (1.0 + jitter[3]) * amount))
    tumble = Quaternion(perp, math.radians(spec["tumble"] * (1.0 + jitter[3]) * amount))
    rot = (spin @ tumble).to_matrix().to_4x4()
    about_centre = Matrix.Translation(centre_w) @ rot @ Matrix.Translation(-centre_w)
    return Matrix.Translation(offset) @ about_centre @ world_land


def screen_point(cam: Camera, frame: float, world: Vector, aspect: float):
    """World point -> frame units, where 1.0 is the frame edge on either axis.

    Same projection as frame_coverage, on a single point, and None behind the camera.
    """
    st = cam.state(frame)
    c = Matrix.LocRotScale(st["loc"], st["quat"], None).inverted() @ world
    depth = -c.z
    if depth <= 1e-6:
        return None
    return (c.x / (depth * st["tan_h"]), c.y / (depth * st["tan_h"] / aspect))


def silhouette_frame(cam: Camera, frame: float, corners, aspect: float):
    """(inside, outside) for a part's whole silhouette, in half-frame units.

    `inside` > 0 means all of it is in shot -- what a landing wants. `outside` > 0 means none
    of it is -- what an entrance wants. Both can be negative at once: that is a part hanging
    over an edge.

    `outside` is a separating axis test, not a distance: a convex hull is off-frame exactly
    when *every* corner is beyond one of the four edges, so it is the best over the four
    edges of the worst corner. Per edge is what makes it right for the entry sectors that
    matter -- a part 100 mm into the foreground is well below the frame *bottom* while its
    horizontal offset is still nearly zero, and a criterion on distance alone cannot see it.
    """
    pts = [screen_point(cam, frame, c, aspect) for c in corners]
    if any(p is None for p in pts):
        return -9.0, -9.0
    inside = 1.0 - max(max(abs(p[0]), abs(p[1])) for p in pts)
    outside = max(min(p[0] for p in pts) - 1.0, min(-p[0] for p in pts) - 1.0,
                  min(p[1] for p in pts) - 1.0, min(-p[1] for p in pts) - 1.0)
    return inside, outside


def entry_basis(rig: Rig, cam: Camera, start: int, land: int, centroid_local: Vector,
                spec: dict, sector: float, jitter: tuple, corners_local=None,
                aspect: float = 16 / 9) -> dict:
    """The entry direction and distance for one part, from the camera's own basis.

    Taking the direction from the shot the viewer is actually watching is what makes "from
    the side of the frame" true rather than approximately true.

    The distance is solved for the frame edge rather than taken as a fixed multiple of the
    half-width, and that distinction turned out to matter more than anything else about the
    swarms. A fixed 1.1 half-widths puts a part whose footprint is already on the far side of
    the board *two* half-widths out, so it spends the first 40 % of its flight off-screen and
    the wave reads as four specks instead of a swarm. Projecting the footprint onto the entry
    direction first and asking for "just outside the edge" gets every part in over the frame
    boundary early and keeps it visible the rest of the way in.

    The widest frame the part crosses is what sizes it, not the frame it sets off on. The
    driver forced that: it sets off while the camera is still in an ADC close-up and lands
    after a pull-back, so sizing its entrance on its own entry frame put it almost on top of
    its footprint.

    That distance is then *solved* against the part's own silhouette rather than trusted,
    because 1.08 half-widths is a claim about a point and a part is not one. Two things break
    it, and both are worse the bigger the part: half a terminal block is 11 mm of the 5 mm
    margin that leaves, and an entry sector pointing into the foreground or the background
    moves a part mostly in *depth*, where a horizontal margin buys almost no vertical one.
    Measured over the whole schedule, 17 of 110 parts were already on screen on the frame
    `key_visibility` made them visible -- the four terminal blocks by 0.27 to 0.56 of a
    half-frame, i.e. materialising in open frame, and the three trimmers by 0.16 to 0.22.
    Nothing in the tables says so and neither `camera_flow.py` nor `frame_pops.py` can:
    the first only looks at the camera, and the second ranks a part appearing during a swarm
    as ordinary sustained motion, because that is exactly what its neighbouring frames show.
    The cost of the fix is x1.55 entry distance at worst and peak part speed 1.24 -> 1.45
    frame-widths/s, all of it on parts that were previously popping.
    """
    st = cam.state(start)
    half_w = 0.0
    for f in (start, (start + land) // 2, land):
        here = cam.state(f)
        half_w = max(half_w,
                     (rig.to_world(f, centroid_local) - here["loc"]).length * here["tan_h"])
    view = (st["aim"] - st["loc"]).normalized()
    right = view.cross(Vector((0, 0, 1)))
    right = right.normalized() if right.length > 1e-6 else Vector((1, 0, 0))
    fwd_h = Vector((view.x, view.y, 0.0))
    fwd_h = fwd_h.normalized() if fwd_h.length > 1e-6 else Vector((0, 1, 0))
    ang = math.radians(sector + jitter[0])
    lateral = (right * math.cos(ang) + fwd_h * math.sin(ang)).normalized()

    # How far along the entry direction the footprint already sits, relative to what the
    # camera is looking at. A part on the entry side needs less distance, one on the far side
    # needs more, and both end up entering at the same place on screen.
    along = (rig.to_world(start, centroid_local) - st["aim"]).dot(lateral)
    reach = max(0.45 * half_w, 1.08 * half_w - along) * spec["reach"] * (1.0 + jitter[1])
    entry = dict(lateral=lateral, right=right, half_w=half_w, reach=reach, grew=1.0,
                 clear=None)
    if not corners_local:
        return entry

    # Walk the distance out until the silhouette clears the frame. Stepped rather than solved
    # in closed form because the projection is not monotone in `reach` for every sector: an
    # entry from the foreground gets *larger* on screen as it moves out, and one from behind
    # the board recedes towards the aim point instead of towards an edge. 5 % steps, and the
    # cap is what stops a sector that can never clear -- the Teensy's, which comes out of
    # depth -- from running away. It does not need it: at 61 mm it is off the frame *top* by
    # 2.0 half-frames on its own entry frame.
    def clear_at(reach: float) -> float:
        entry["reach"] = reach
        return silhouette_frame(
            cam, start,
            [flight_world(rig, entry, Matrix.Translation(p), Matrix.Identity(4),
                          centroid_local, start, start, land, spec, jitter).translation
             for p in corners_local], aspect)[1]

    best = (clear_at(reach), reach)
    for i in range(ENTRY_TRIES):
        if best[0] >= ENTRY_PAD:
            break
        grown = reach * ENTRY_GROW ** (i + 1)
        got = clear_at(grown)
        if got > best[0]:
            best = (got, grown)
    entry.update(reach=best[1], clear=best[0], grew=best[1] / reach)
    return entry


# --------------------------------------------------------------------- keyframe plumbing


def fcurves_of(holder):
    """Blender 4.4 moved fcurves into action layers/slots and kept `action.fcurves` as a
    compatibility view that is empty for slotted actions. Try both."""
    ad = getattr(holder, "animation_data", None)
    if not ad or not ad.action:
        return []
    out = list(getattr(ad.action, "fcurves", []))
    if out:
        return out
    for layer in getattr(ad.action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def set_interp(holder, path, interp="LINEAR", easing="AUTO"):
    for fc in fcurves_of(holder):
        if fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.easing = easing


def key_visibility(obj, frame: int):
    """Hidden until `frame`, visible from it. Stepped, so nothing half-fades in."""
    for path in ("hide_render", "hide_viewport"):
        setattr(obj, path, True)
        obj.keyframe_insert(path, frame=max(1, frame - 1))
        setattr(obj, path, False)
        obj.keyframe_insert(path, frame=frame)
        set_interp(obj, path, interp="CONSTANT")


def key_value(node, series, interp="CUBIC", easing="EASE_IN_OUT"):
    """Keyframe a Value node's output from [(frame, value), ...]."""
    for frame, value in series:
        node.outputs[0].default_value = value
        node.outputs[0].keyframe_insert("default_value", frame=frame)
    for fc in fcurves_of(node.id_data):
        if fc.data_path == f'nodes["{node.name}"].outputs[0].default_value':
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                kp.easing = easing


# ---------------------------------------------------------------- fabrication shader rig


class Nodes:
    """Small helper over a shader node tree: create, feed, and lay out left to right."""

    def __init__(self, tree, prefix="FAB_"):
        self.tree, self.prefix, self.rows = tree, prefix, {}

    def new(self, idname, name, column=0, **props):
        node = self.tree.nodes.new(idname)
        node.name = node.label = self.prefix + name
        row = self.rows.get(column, 0)
        self.rows[column] = row + 1
        node.location = (-3000 + column * 250, 1400 - row * 58)
        node.hide = True
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def _feed(self, node, index, value):
        if hasattr(value, "is_linked"):
            self.tree.links.new(value, node.inputs[index])
        else:
            node.inputs[index].default_value = value

    def math(self, op, a, b=None, column=1, name=None, clamp=False):
        node = self.new("ShaderNodeMath", name or f"m{len(self.tree.nodes)}", column,
                        operation=op, use_clamp=clamp)
        self._feed(node, 0, a)
        if b is not None:
            self._feed(node, 1, b)
        return node.outputs[0]

    def madd(self, a, b, c, column=1, name=None):
        """a * b + c, in one node. Kept separate from math() so that helper can go on
        taking `column` as its fourth positional argument."""
        node = self.new("ShaderNodeMath", name or f"ma{len(self.tree.nodes)}", column,
                        operation="MULTIPLY_ADD")
        for i, v in enumerate((a, b, c)):
            self._feed(node, i, v)
        return node.outputs[0]

    def maprange(self, value, fmin, fmax, tmin, tmax, column=1, name=None):
        # Indices, not names: ShaderNodeMapRange repeats "From Min" etc. for its vector
        # variant, and the float sockets are always the first five.
        node = self.new("ShaderNodeMapRange", name or f"r{len(self.tree.nodes)}", column,
                        clamp=True)
        for i, v in enumerate((value, fmin, fmax, tmin, tmax)):
            self._feed(node, i, v)
        return node.outputs["Result"]

    def value(self, name, default, column=0):
        node = self.new("ShaderNodeValue", name, column)
        node.outputs[0].default_value = default
        return node

    def lerp(self, a, b, t, column=1):
        """a + (b - a) * t, in Math nodes. ShaderNodeMix's float sockets are only reachable
        by identifier and their index order has moved between releases; Math cannot break."""
        return self.madd(self.math("SUBTRACT", b, a, column), t, a, column + 1)


def morph_taps(nx: Nodes, image, uv, radius, op: str, size_mm, tag: str):
    """Ring-tap morphology on a layer image: MAXIMUM dilates it, MINIMUM erodes it.

    Dilating the mask is the same operation as eroding its openings, which is how a pad
    grows from its centre out to the exact real aperture instead of fading up: at radius
    0.62 mm every opening on this board is closed, and at 0 the taps coincide so the result
    is the layer exactly as plotted. Eroding the silkscreen does the mirror image for
    strokes, text and the logos.

    Offsets are millimetres converted per axis, because the layer bounds are not square.
    Returns (front, back): R and G are the front and back layer.
    """
    w_mm, h_mm = size_mm
    taps = []
    for k in range(TAPS):
        ang = 2 * math.pi * k / TAPS
        dx = nx.math("MULTIPLY", radius.outputs[0], math.cos(ang) / w_mm, 2, f"{tag}dx{k}")
        dy = nx.math("MULTIPLY", radius.outputs[0], math.sin(ang) / h_mm, 2, f"{tag}dy{k}")
        comb = nx.new("ShaderNodeCombineXYZ", f"{tag}c{k}", 3)
        nx.tree.links.new(dx, comb.inputs["X"])
        nx.tree.links.new(dy, comb.inputs["Y"])
        mapping = nx.new("ShaderNodeMapping", f"{tag}map{k}", 4, vector_type="POINT")
        nx.tree.links.new(uv, mapping.inputs["Vector"])
        nx.tree.links.new(comb.outputs[0], mapping.inputs["Location"])
        tex = nx.new("ShaderNodeTexImage", f"{tag}tex{k}", 5, image=image,
                     interpolation="Linear")
        nx.tree.links.new(mapping.outputs[0], tex.inputs["Vector"])
        sep = nx.new("ShaderNodeSeparateColor", f"{tag}sep{k}", 6)
        nx.tree.links.new(tex.outputs["Color"], sep.inputs["Color"])
        taps.append(sep)

    def reduce(channel):
        acc = taps[0].outputs[channel]
        for sep in taps[1:]:
            acc = nx.math(op, acc, sep.outputs[channel], 7)
        return acc

    return reduce("Red"), reduce("Green")


class Fabrication:
    """Rewire the imported board material so the board can be manufactured on camera.

    Nothing here draws anything. Every reveal is one of the importer's own layer images,
    gated spatially or morphologically. The eight float sockets on the PCB Shader node are
    the whole interface, plus the Solder Mask node's own F_Cu/B_Cu -- so the copper relief
    under the mask matches the copper that is actually there -- and the Board Edge node's
    Mix, so the rim is bare laminate until the mask lands.
    """

    def __init__(self, material, size_mm):
        self.mat, self.tree, self.size_mm = material, material.node_tree, size_mm
        tree = self.tree
        self.shader = next((n for n in tree.nodes if n.bl_idname == "ShaderNodePcbShader"),
                           None)
        if self.shader is None:
            sys.exit("board material has no PCB Shader node -- was it imported RASTERIZED?")
        self.solder_mask = next(
            (n for n in tree.nodes if n.bl_idname == "ShaderNodeBsdfPcbSolderMask"), None)
        self.board_edge = next(
            (n for n in tree.nodes if n.bl_idname == "ShaderNodeBsdfPcbBoardEdge"), None)
        self.images, self.orig = {}, {}
        for socket, layer in (("F_Cu", "Cu"), ("F_Mask", "Mask"), ("F_SilkS", "SilkS"),
                              ("F_Paste", "Paste")):
            sep = self.shader.inputs[socket].links[0].from_node    # SeparateColor
            self.orig[layer] = sep
            self.images[layer] = sep.inputs["Color"].links[0].from_node.image
        self.nx = Nodes(tree)
        self.controls = {}
        self._build()

    def _axis(self, phi_deg, name, wobble=None):
        """s = x*cos(phi) + y*sin(phi) in millimetres, from UV.

        The etch fronts get a noise wobble, so the receding copper has a chemical edge
        rather than a ruled line. The silkscreen and paste fronts get none: those are
        printing and reflow, and a wavy front would read as an artefact.
        """
        nx, (w, h) = self.nx, self.size_mm
        wobble = ETCH["wobble"] if wobble is None else wobble
        phi = math.radians(phi_deg)
        sx = nx.math("MULTIPLY", self.u, w * math.cos(phi), 1, f"{name}sx")
        sy = nx.math("MULTIPLY", self.v, h * math.sin(phi), 1, f"{name}sy")
        s = nx.math("ADD", sx, sy, 2, f"{name}s")
        if not wobble:
            return s
        centred = nx.math("SUBTRACT", self.noise, 0.5, 2, f"{name}n0")
        return nx.math("ADD", s, nx.math("MULTIPLY", centred, wobble * 2.0, 3,
                                         f"{name}n1"), 3, f"{name}sn")

    def _build(self):
        nx, tree = self.nx, self.tree
        coord = nx.new("ShaderNodeTexCoord", "coord", 0)
        sep_uv = nx.new("ShaderNodeSeparateXYZ", "sep_uv", 1)
        tree.links.new(coord.outputs["UV"], sep_uv.inputs["Vector"])
        self.u, self.v = sep_uv.outputs["X"], sep_uv.outputs["Y"]
        sep_obj = nx.new("ShaderNodeSeparateXYZ", "sep_obj", 1)
        tree.links.new(coord.outputs["Object"], sep_obj.inputs["Vector"])
        is_bot = nx.math("LESS_THAN", sep_obj.outputs["Z"], 0.0, 2, "is_bot")

        noise = nx.new("ShaderNodeTexNoise", "noise", 1, noise_dimensions="2D")
        tree.links.new(coord.outputs["UV"], noise.inputs["Vector"])
        noise.inputs["Scale"].default_value = ETCH["wobble_scale"]
        noise.inputs["Detail"].default_value = 2.0
        self.noise = noise.outputs["Fac"]

        edge = nx.new("ShaderNodeAttribute", "edge", 0, attribute_name="pcb_board_edge")
        edge_inv = nx.math("SUBTRACT", 1.0, edge.outputs["Fac"], 1, "edge_inv")

        c = self.controls
        for side, phi in (("top", ETCH["phi_top"]), ("bot", ETCH["phi_bot"])):
            lo, _hi = axis_range(phi, self.size_mm)
            c[f"front_{side}"] = nx.value(f"front_{side}", lo - ETCH["width"])
        for name, default in (("pad_r", PAD_R), ("silk_r", SILK_R), ("silk_front", 0.0),
                              ("paste_front", 0.0), ("mask_f", 0.0), ("mask_b", 0.0),
                              ("plate", 0.0), ("edge_mix", 0.0)):
            c[name] = nx.value(name, default)
        width = nx.value("etch_w", ETCH["width"])

        # --- copper: a flood, minus a travelling front --------------------------------
        cu, band = {}, {}
        for side, phi, chan in (("top", ETCH["phi_top"], "Red"),
                                ("bot", ETCH["phi_bot"], "Green")):
            s = self._axis(phi, side)
            front = c[f"front_{side}"].outputs[0]
            lo = nx.math("SUBTRACT", front, width.outputs[0], 4, f"{side}lo")
            hi = nx.math("ADD", front, width.outputs[0], 4, f"{side}hi")
            # 0 behind the front (etched away), 1 ahead of it (still copper-clad). Gated by
            # the board-edge attribute, so the rim shows laminate rather than a copper slab.
            flood = nx.maprange(s, lo, hi, 0.0, 1.0, 5, f"{side}flood")
            flood = nx.math("MULTIPLY", flood, edge_inv, 6, f"{side}floodg")
            cu[side] = nx.math("MAXIMUM", self.orig["Cu"].outputs[chan], flood, 7,
                               f"{side}cu")
            # A narrow triangle peaking on the front: the wet line where copper is going.
            rise = nx.maprange(s, lo, front, 0.0, 1.0, 5, f"{side}br")
            fall = nx.maprange(s, front, hi, 1.0, 0.0, 5, f"{side}bf")
            band[side] = nx.math("MULTIPLY", rise, fall, 6, f"{side}band")

        cu_f, cu_b = cu["top"], cu["bot"]
        cu_here = nx.lerp(cu_f, cu_b, is_bot, 8)
        band_here = nx.lerp(band["top"], band["bot"], is_bot, 8)
        band_cu = nx.math("MULTIPLY", band_here, cu_here, 10, "band_cu")

        # --- mask: real openings, developed open during the pads phase ----------------
        mask_er = morph_taps(nx, self.images["Mask"], coord.outputs["UV"], c["pad_r"],
                             "MAXIMUM", self.size_mm, "mk")
        # Below 0.02 mm the eroded (linear-sampled) version and the layer's own cubic
        # sample differ by less than a pixel, so hand back to the original there: the
        # finished board is then exactly the board the stills render.
        pad_blend = nx.maprange(c["pad_r"].outputs[0], 0.0, 0.02, 0.0, 1.0, 1, "padblend")
        mask = [nx.lerp(self.orig["Mask"].outputs[ch], er, pad_blend, 8)
                for ch, er in (("Red", mask_er[0]), ("Green", mask_er[1]))]
        mask_f = nx.math("MULTIPLY", mask[0], c["mask_f"].outputs[0], 10, "mask_f")
        mask_b = nx.math("MULTIPLY", mask[1], c["mask_b"].outputs[0], 10, "mask_b")

        # --- silkscreen: strokes widen, and the printing travels ----------------------
        silk_er = morph_taps(nx, self.images["SilkS"], coord.outputs["UV"], c["silk_r"],
                             "MINIMUM", self.size_mm, "sk")
        silk_blend = nx.maprange(c["silk_r"].outputs[0], 0.0, 0.004, 0.0, 1.0, 1,
                                 "silkblend")
        sf = c["silk_front"].outputs[0]
        drawn = nx.maprange(self._axis(ETCH["phi_top"], "silk", wobble=0.0),
                            nx.math("SUBTRACT", sf, SILK_RAMP, 4, "sklo"),
                            nx.math("ADD", sf, SILK_RAMP, 4, "skhi"), 1.0, 0.0, 5, "drawn")
        silk = [nx.math("MULTIPLY", nx.lerp(self.orig["SilkS"].outputs[ch], er,
                                            silk_blend, 8), drawn, 10, f"silk_{ch}")
                for ch, er in (("Red", silk_er[0]), ("Green", silk_er[1]))]

        # --- paste: solder appears under the parts as the waves land ------------------
        pf = c["paste_front"].outputs[0]
        wetted = nx.maprange(self._axis(20.0, "paste", wobble=0.0),
                             nx.math("SUBTRACT", pf, PASTE_RAMP, 4, "pslo"),
                             nx.math("ADD", pf, PASTE_RAMP, 4, "pshi"), 1.0, 0.0, 5,
                             "wetted")
        paste = [nx.math("MULTIPLY", self.orig["Paste"].outputs[ch], wetted, 10,
                         f"paste_{ch}") for ch in ("Red", "Green")]

        # --- exposed copper: bare laminate -> ENIG, with the etch line ----------------
        enig = self.shader.inputs["Exposed Copper"].links[0].from_socket
        plated = nx.new("ShaderNodeMixShader", "mix_plate", 11)
        tree.links.new(c["plate"].outputs[0], plated.inputs["Fac"])
        tree.links.new(self._finish("bare", *COPPER_BARE), plated.inputs[1])
        tree.links.new(enig, plated.inputs[2])
        etching = nx.new("ShaderNodeMixShader", "mix_etch", 12)
        tree.links.new(band_cu, etching.inputs["Fac"])
        tree.links.new(plated.outputs[0], etching.inputs[1])
        tree.links.new(self._finish("wet", *COPPER_ETCH), etching.inputs[2])

        for socket, out in (("F_Cu", cu_f), ("B_Cu", cu_b), ("F_Mask", mask_f),
                            ("B_Mask", mask_b), ("F_SilkS", silk[0]), ("B_SilkS", silk[1]),
                            ("F_Paste", paste[0]), ("B_Paste", paste[1])):
            tree.links.new(out, self.shader.inputs[socket])
        tree.links.new(etching.outputs[0], self.shader.inputs["Exposed Copper"])
        if self.solder_mask is not None:
            tree.links.new(cu_f, self.solder_mask.inputs["F_Cu"])
            tree.links.new(cu_b, self.solder_mask.inputs["B_Cu"])
        self.edge_mix_final = 1.0
        if self.board_edge is not None:
            self.edge_mix_final = self.board_edge.inputs["Mix"].default_value
            tree.links.new(c["edge_mix"].outputs[0], self.board_edge.inputs["Mix"])
        # What the films are made of, taken from the board rather than chosen again.
        self.mask_color = (0.19, 0.07, 0.38)
        self.mask_roughness = 0.45
        if self.solder_mask is not None:
            self.mask_color = tuple(self.solder_mask.inputs["Light Color"].default_value[:3])
            self.mask_roughness = self.solder_mask.inputs["Roughness"].default_value

    def _finish(self, name, color_hex, roughness, texture):
        node = self.nx.new("ShaderNodeBsdfPcbSurfaceFinish", name, 10,
                           surface_finish="CUSTOM")
        node.inputs["Color"].default_value = (*hex2lin(color_hex), 1.0)
        node.inputs["Roughness"].default_value = roughness
        node.inputs["Texture Strength"].default_value = texture
        return node.outputs["BSDF"]

    def keyframe(self, paste_span):
        c = self.controls
        # A front is the *centre* of a ramp +-width wide, and the noise displaces s by up to
        # +-wobble, so parking it at lo - width is not far enough: a corner of the board
        # comes out 70 % copper on frame 1 instead of 100 %. The margin is the sum.
        margin = ETCH["width"] + ETCH["wobble"]
        for side, phi, span in (("top", ETCH["phi_top"], F_ETCH_TOP),
                                ("bot", ETCH["phi_bot"], F_ETCH_BOT)):
            lo, hi = axis_range(phi, self.size_mm)
            key_value(c[f"front_{side}"], [(1, lo - margin), (span[0], lo - margin),
                                           (span[1], hi + margin)])
        # The films touch a few frames apart, and each hands over to the board's own mask
        # across F_HANDOFF frames. Both surfaces are the same purple and coincident, so the
        # crossfade is invisible -- it exists so that nothing pops.
        key_value(c["mask_f"], [(F_FILM_CONTACT[0] - 1, 0.0),
                                (F_FILM_CONTACT[0] + F_HANDOFF, 1.0)])
        key_value(c["mask_b"], [(F_FILM_CONTACT[1] - 1, 0.0),
                                (F_FILM_CONTACT[1] + F_HANDOFF, 1.0)])
        key_value(c["edge_mix"], [(F_FILM_CONTACT[0] - 1, 0.0),
                                  (F_FILM_CONTACT[1] + F_HANDOFF, self.edge_mix_final)])
        key_value(c["pad_r"], [(1, PAD_R), (F_PADS[0], PAD_R), (F_PADS[1], 0.0)])
        key_value(c["plate"], [(F_PADS[0], 0.0), (F_PADS[1], 1.0)])
        key_value(c["silk_r"], [(1, SILK_R), (F_SILK[0], SILK_R), (F_SILK[1], 0.0)])
        lo_s, hi_s = axis_range(ETCH["phi_top"], self.size_mm)
        key_value(c["silk_front"], [(1, lo_s - SILK_RAMP), (F_SILK[0], lo_s - SILK_RAMP),
                                    (F_SILK[1], hi_s + SILK_RAMP)])
        lo_p, hi_p = axis_range(20.0, self.size_mm)
        key_value(c["paste_front"], [(1, lo_p - PASTE_RAMP),
                                     (paste_span[0], lo_p - PASTE_RAMP),
                                     (paste_span[1], hi_p + PASTE_RAMP)])


# ---------------------------------------------------------------------------- mask films


def build_films(board_obj, mask_image, size_mm, color, roughness) -> dict:
    """Two conformal purple films, built from the board's own top and bottom faces.

    Not an approximation of the outline: it *is* the outline, with every cutout and drill
    already in it, and it inherits the board's UVs, so the alpha can be the real mask layer
    -- the openings in the film are the openings on the board. Through-hole barrels carry
    the importer's `pcb_through_holes` flag and are dropped, which is what stops a film from
    stretching a skin across the holes.

    Its openings stay shut for its whole life: the film exists only between F_FILM_FLY and
    the handoff, and the openings develop afterwards, on the board. So the tap radius here
    is a constant, not an animated control.
    """
    out = {}
    for side, sign in (("TOP", 1.0), ("BOT", -1.0)):
        mesh = board_obj.data.copy()
        mesh.name = f"MASK_FILM_{side}"
        bm = bmesh.new()
        bm.from_mesh(mesh)
        holes = bm.faces.layers.int.get("pcb_through_holes")
        doomed = [f for f in bm.faces
                  if not (f.normal.z * sign > 0.9
                          and f.calc_center_median().z * sign > 0
                          and not (holes is not None and f[holes]))]
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                         context="VERTS")
        bm.to_mesh(mesh)
        bm.free()
        if not len(mesh.polygons):
            sys.exit(f"mask film {side}: no faces survived the extraction")

        obj = bpy.data.objects.new(f"MASK_FILM_{side}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = board_obj.matrix_world.copy()

        mat = bpy.data.materials.new(f"MASK_FILM_{side}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        nx = Nodes(mat.node_tree, prefix="FILM_")
        coord = nx.new("ShaderNodeTexCoord", "coord", 0)
        er_f, er_b = morph_taps(nx, mask_image, coord.outputs["UV"],
                                nx.value("r", PAD_R), "MAXIMUM", size_mm, "f")
        alpha_node = nx.value("alpha", FILM_ALPHA_AIR)
        alpha = nx.math("MULTIPLY", er_f if sign > 0 else er_b, alpha_node.outputs[0], 9,
                        f"a{side}")
        mat.node_tree.links.new(alpha, bsdf.inputs["Alpha"])
        mesh.materials.clear()
        mesh.materials.append(mat)
        out[side] = dict(obj=obj, alpha=alpha_node, sign=sign)
    print(f"  mask films: {len(out['TOP']['obj'].data.polygons)} top faces, "
          f"{len(out['BOT']['obj'].data.polygons)} bottom faces")
    return out


def animate_films(films):
    """Fly each film in along the board normal, land it, then hand over and hide it.

    Keyed in board-local space on purpose: "from above" for a conformal coating means along
    the board's own normal, and the rig carries it into the world. The arrival is a settle
    rather than a stop -- a slight overscale that relaxes and a damped ripple on approach --
    so it reads as a film conforming rather than a slab landing.
    """
    for side, film in films.items():
        obj, sign = film["obj"], film["sign"]
        contact = F_FILM_CONTACT[0] if sign > 0 else F_FILM_CONTACT[1]
        start = F_FILM_FLY if sign > 0 else F_FILM_FLY + 6
        base = obj.matrix_basis.copy()
        gap = 0.00004 * sign            # clear of the board, well under the mask relief
        key_visibility(obj, start)
        for frame in range(start, contact + 1):
            u = (frame - start) / max(1, contact - start)
            e = smootherstep(u)
            height = 0.055 * (1.0 - e) * sign
            ripple = 0.0012 * (1.0 - e) ** 2 * math.sin(u * 9.0) * sign
            scale = 1.0 + 0.016 * (1.0 - e)
            tilt = math.radians(5.0 * (1.0 - e)) * sign
            obj.matrix_basis = (Matrix.Translation((0.0, 0.0, height + ripple + gap))
                                @ Matrix.Rotation(tilt, 4, "Y")
                                @ Matrix.Diagonal((scale, scale, 1.0, 1.0)) @ base)
            for path in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(path, frame=frame)
        for path in ("location", "rotation_euler", "scale"):
            set_interp(obj, path, interp="LINEAR")
        # Alpha starts at zero, not at FILM_ALPHA_AIR. `key_visibility` is a hard step -- it has
        # to be, since a fully transparent surface still costs rays -- so keying the film
        # visible and opaque on the same frame made a board-sized purple sheet appear from
        # nothing, mid-frame, in one frame. It was doing that at f525 and f531 and it is the
        # single most visible thing in the draft. Fading up over F_FILM_FADE while it is already
        # descending costs nothing: at alpha 0 the sheet renders as if it were not there.
        key_value(film["alpha"], [(start, 0.0), (start + F_FILM_FADE, FILM_ALPHA_AIR),
                                  (contact, 1.0), (contact + F_HANDOFF, 0.0)], interp="LINEAR")
        # Gone, not merely transparent: a coincident transparent surface still costs rays
        # and still tints what is behind it.
        for frame, hidden in ((contact + F_HANDOFF, False),
                              (contact + F_HANDOFF + 1, True)):
            obj.hide_render = obj.hide_viewport = hidden
            obj.keyframe_insert("hide_render", frame=frame)
            obj.keyframe_insert("hide_viewport", frame=frame)
        for path in ("hide_render", "hide_viewport"):
            set_interp(obj, path, interp="CONSTANT")


# -------------------------------------------------------------------------------- lights


def build_riders(strength: float, diag: float):
    """Two lights that ride with the board rather than standing in the studio.

    SWEEP is a narrow strip: the controlled travelling highlight that walks along the etch
    front, narrows onto a hero landing, and crosses the metal in the finale. UNDER is a
    broad box below the board, on only while the underside is what the shot is about --
    the four studio lights are all above, so bare copper on the bottom face is a black
    mirror without it.

    Both store watts *at 0.2 m*, and bake_lights rescales by the light's own distance each
    frame. That matters: build_lighting's `(d / 0.2) ** 2` makes irradiance depend on the
    base number alone, and reusing the studio's d for a strip 42 mm off the board over-lit
    it by (220/42)^2 = 27x. That was the whole reason the first probe pass came back with
    white components and blown silkscreen.
    """
    out = {}
    for name, base, shape, size in (("SWEEP", SWEEP_BASE_WATTS, "RECTANGLE", None),
                                    ("UNDER", UNDER_BASE_WATTS, "SQUARE", diag * 1.15)):
        light = bpy.data.lights.new(name, type="AREA")
        light.shape = shape
        light.energy = 0.0
        light.color = (1.0, 0.98, 0.95) if name == "SWEEP" else (0.96, 0.97, 1.0)
        light["base_energy"] = base * strength
        if size:
            light.size = size
        obj = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(obj)
        out[name] = obj
    return out


def bake_lights(lights, riders, rig: Rig, cam: Camera, heroes_local: dict, diag: float,
                end: int):
    """Ride the calibrated rig, and walk the two board-mounted lights along with it.

    The look's ratio and the calibrated level are already in each studio light's energy, so
    `light` only rides the whole rig and fillx/rimx only narrow it onto a landing: the
    calibration survives either way.
    """
    sweep, under = riders["SWEEP"], riders["UNDER"]
    # `at` is resolved into the beat table *before* splining, not looked up per frame after.
    # Per-frame lookup made the strip's position a step function: it is a narrow, bright,
    # board-mounted highlight, and it teleported 40 mm the frame it grabbed the ADC and 76 mm
    # between the driver and the Teensy. That was always here -- v2's busier camera merely hid
    # it, and a calmer one would have put a lighting pop on the ADC's hero reveal. Substituting
    # the hero positions here leaves px/py a single continuous spline that *travels* between
    # them, which is what the camera is doing over the same frames anyway.
    rows = []
    for beat in SWEEP_BEATS:
        vals, at_name = list(beat[:-1]), beat[-1]
        if at_name is not None:
            vals[2] = heroes_local[at_name].x * 1000.0
            vals[3] = heroes_local[at_name].y * 1000.0
        rows.append(vals)
    fs = [r[0] for r in rows]
    ch = {name: Spline(fs, [r[1 + i] for r in rows])
          for i, name in enumerate(SWEEP_CHANNELS)}
    ufs = [b[0] for b in UNDER_BEATS]
    under_e = Spline(ufs, [b[1] for b in UNDER_BEATS])
    under_z = -diag * 0.55
    prev = {}

    def aim_at(obj, target):
        euler = (target - obj.location).normalized().to_track_quat("-Z", "Y")
        prev[obj.name] = euler.to_euler("XYZ", prev[obj.name]) if obj.name in prev \
            else euler.to_euler()
        obj.rotation_euler = prev[obj.name]

    for frame in range(1, end + 1):
        st = cam.state(frame)
        for name, obj in lights.items():
            ride = st["light"] * {"FILL": st["fillx"], "RIM": st["rimx"]}.get(name, 1.0)
            obj.data.energy = obj.data["base_energy"] * studio.LOOKS[LOOK][name] * ride
            obj.data.keyframe_insert("energy", frame=frame)

        px, py = ch["px"](frame), ch["py"](frame)
        pz = ch["pz"](frame) / 1000.0
        sweep.location = rig.to_world(frame, Vector((px / 1000.0, py / 1000.0, pz)))
        aim_at(sweep, rig.to_world(frame, Vector((px / 1000.0, py / 1000.0, 0.0))))
        # Watts at 0.2 m, rescaled to wherever the light actually is, so `e` means the same
        # thing whether the strip is 24 mm off a hero or 52 mm off the whole board.
        sweep.data.energy = (sweep.data["base_energy"] * max(0.0, ch["e"](frame))
                             * (max(0.012, abs(pz)) / 0.2) ** 2)
        sweep.data.size = max(0.002, ch["sx"](frame) / 1000.0)
        sweep.data.size_y = max(0.002, ch["sy"](frame) / 1000.0)

        under.location = rig.to_world(frame, Vector((0.0, 0.0, under_z)))
        aim_at(under, rig.to_world(frame, Vector((0.0, 0.0, 0.0))))
        under.data.energy = (under.data["base_energy"] * max(0.0, under_e(frame))
                             * (abs(under_z) / 0.2) ** 2)

        for obj in (sweep, under):
            obj.keyframe_insert("location", frame=frame)
            obj.keyframe_insert("rotation_euler", frame=frame)
            obj.data.keyframe_insert("energy", frame=frame)
        for path in ("size", "size_y"):
            sweep.data.keyframe_insert(path, frame=frame)

    for holder in ([sweep, under, sweep.data, under.data]
                   + [o.data for o in lights.values()]):
        for fc in fcurves_of(holder):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


# ---------------------------------------------------------------------------- targets


def group_targets(groups: dict, pos_of: dict, top_of: dict | None = None) -> dict:
    """Aim points for the wave groups TARGET_BEATS names, taken from the parts themselves.

    A group rather than a designator, for the same reason the heroes are resolved by part
    number: J8 has been renumbered before. The centre of the group, so a second connector on
    a later board revision cannot silently go unshown.
    """
    out = {}
    for label in SUBJECT_GROUPS:
        refs = groups.get(label) or []
        if not refs:
            continue
        c = sum((pos_of[r] for r in refs), Vector()) / len(refs)
        # A little above the part, not at its pads -- same reason as heroes_local.
        z = (max(top_of[r] for r in refs) + 0.004) if top_of else c.z + 0.006
        aim = SUBJECT_AIM[label]
        out[label] = Vector((c.x * aim["bias"] + aim["nudge"][0] / 1000.0,
                             c.y * aim["bias"] + aim["nudge"][1] / 1000.0, z))
    return out


def build_targets(named_local: dict, plan: dict, pos_local: dict, size_mm, end: int):
    """Named aim points in board-local space, some of them moving.

    `etch` rides the etch front, so focus is on the region actually being fabricated;
    `swarm` rides the centroid of whatever is in the air, so attention is on the group
    arriving rather than on the geometric centre of the board.
    """
    # Each front's aim rides a smootherstep across the span front_travel says is clamp-free,
    # rather than a spline through the front's own raw `s`. Two things follow: the aim's
    # velocity is zero at both ends of its travel, so nothing corners when the clamp is
    # finally reached, and it cannot overshoot -- a natural cubic through a flat-rise-flat
    # set does both, which is what the first version keyed here.
    def ride(frame, span, phi):
        s0, s1 = front_travel(phi, size_mm)
        t = smootherstep((frame - span[0]) / max(1, span[1] - span[0]))
        p = front_point(s0 + (s1 - s0) * t, phi, size_mm)
        # Damped towards the board centre, not followed -- see ETCH_AIM_BIAS. The *direction*
        # of the shift is what reads as "the front is over there"; its full amplitude only
        # costs the rest of the board.
        return Vector((p.x * ETCH_AIM_BIAS, p.y * ETCH_AIM_BIAS, p.z))

    def etch(frame):
        # Cross-fade from the top front to the bottom one over the overlap, so the aim
        # travels rather than jumping when the second front takes over. The two fronts run
        # on opposite axes and meet at the same end of the board, so the aim goes out along
        # it and comes back -- and it turns around at zero speed, where the fronts hand over.
        w = smootherstep((frame - F_ETCH_TOP[1]) / max(1, F_ETCH_BOT[1] - F_ETCH_TOP[1]))
        return ride(frame, F_ETCH_TOP, ETCH["phi_top"]).lerp(
            ride(frame, F_ETCH_BOT, ETCH["phi_bot"]), w)

    airborne = {}
    for ref, (start, land, _s, _spec) in plan.items():
        for f in range(start, land + 1):
            airborne.setdefault(f, []).append(pos_local[ref])
    raw = [sum(airborne[f], Vector()) / len(airborne[f]) if f in airborne
           else Vector((0.0, 0.0, 0.004)) for f in range(1, end + 1)]
    # Smoothed hard: the raw centroid of a swarm jitters as parts land, and a focus target
    # that jitters is focus hunting. The window is ~5 s of total support, scaled with the
    # waves themselves -- at v2's +-41 frames against these 21 s of waves the aim would
    # wander visibly, and a wandering aim is an uncontrolled velocity added to a camera move
    # designed to have none.
    #
    # Three narrow passes, not one wide one. A boxcar's derivative is discontinuous wherever
    # the signal under it has a step, and the airborne set steps every time a wave empties,
    # so one pass leaves a corner in the aim's velocity at each window edge. camera_flow.py
    # measured that as the worst lurch left in the piece -- 27.6x the median rate of change,
    # at f1450, which is exactly one window before the last supporting part lands. Three
    # boxes convolve to a C2 kernel of the same total width.
    smooth = raw
    for _ in range(3):
        win, prev = 26, smooth
        smooth = []
        for i in range(len(prev)):
            a, b = max(0, i - win), min(len(prev), i + win + 1)
            smooth.append(sum(prev[a:b], Vector()) / (b - a))

    # Damped toward the board centre rather than followed outright. The last waves are the
    # connectors, which sit at one end of the board, so an undamped centroid walks 77 mm out
    # to the Harting and is then pulled straight back by the handoff to the ADC at the other
    # end -- a 134 deg reversal in the aim's own travel, which is the sudden recentring this
    # whole rework exists to remove. At 0.6 the aim still leans towards whatever is arriving,
    # which is the point of the target, without ever committing to a trip it has to undo.
    swarm_bias = 0.6

    def swarm(frame):
        p = smooth[max(0, min(int(frame) - 1, len(smooth) - 1))]
        return Vector((p.x * swarm_bias, p.y * swarm_bias, p.z))

    targets = {"board": lambda f: Vector((0.0, 0.0, 0.006)), "etch": etch, "swarm": swarm}
    for name, point in named_local.items():
        targets[name] = (lambda p: (lambda f: p))(point)
    return targets


# ------------------------------------------------------------------------- diagnostics


# The storyboard's beats, plus a movement frame between most pairs of them. The second kind
# earns its place: a frame chosen to look good never shows smearing, focus hunting or
# clipping, and those are what a probe pass is for. Captions are written out beside the
# frames so the contact sheet and this table cannot drift apart.
PROBES = (
    (1, "raw copper, grazing"),
    (90, "copper, camera travelling"),
    (200, "top etch front entering"),
    (270, "top etch, mid-board"),
    (330, "top copper complete"),
    (470, "board turned over, bottom etch"),
    (545, "bottom copper complete"),
    (585, "both mask films airborne"),
    (632, "film contact, board coming back up"),
    (700, "pads developing, ENIG"),
    (800, "silkscreen drawing"),
    (870, "fabricated, unpopulated"),
    (950, "first regional swarm"),
    (1120, "dense swarm, lights raking"),
    (1300, "swarm at full rate"),
    (1420, "terminals down, last headers"),
    (1480, "aim crossing to the connector"),
    (1524, "Harting lands, presented"),
    (1580, "connector held, ADC inbound"),
    (1690, "ADC hovering over its pads"),
    (1720, "ADC landing"),
    (1810, "traverse toward the driver"),
    (1890, "driver hovering over its pads"),
    (1880, "closest point of the piece"),
    (1912, "driver landing"),
    (2010, "retreat begins, Teensy out of depth"),
    (2080, "Teensy crossing frame"),
    (2140, "Teensy landing"),
    (2210, "rake across the Harting pins"),
    (2320, "rake across the Teensy / USB"),
    (2430, "rake over the power section"),
    (2520, "last frame, still moving"),
)
PROBE_FRAMES = tuple(f for f, _ in PROBES)


def print_entries(entries: dict, showcased: dict, silhouettes: bool = True):
    """Both ends of every flight, as the viewer gets them: off frame when the part appears,
    in frame when it lands.

    The two faults this reports were both found by watching, not by a check -- a terminal
    block materialising in open frame, and the Harting landing outside the right edge -- and
    neither of the other two tools can see either. `camera_flow.py` measures the camera and
    knows nothing about parts; `frame_pops.py` measures rendered frames and ranks a part
    appearing mid-swarm as ordinary sustained motion, because its neighbouring frames are
    just as busy. This is the check that would have caught them, and it is cheap.
    """
    what = "silhouettes" if silhouettes else "centres only -- the silhouette needs the scene"
    print(f"\n  entrances and landings ({what}). off > 0 = wholly out of shot when it "
          f"appears; in > 0 = wholly in shot when it lands")
    print(f"    {'ref':6s} {'spawn':>6s} {'land':>5s} {'sec':>4s} {'off@spawn':>10s} "
          f"{'grew':>5s} {'in@land':>8s}")
    rows = sorted(entries.items(), key=lambda kv: kv[1][3])
    popped = [r for r in rows if r[1][3] < 0.0]
    # Only the parts the storyboard promises to show are held to being in frame when they
    # land: everything else lands wherever its footprint is, and at a 135 mm frame on a 165 mm
    # board a passive at either end is legitimately over the edge.
    hidden = [r for r in rows if r[0] in showcased and r[1][5] < 0.0]
    shown = [r for r in rows if r[0] in showcased]
    for ref, (start, land, sector, off, grew, inside) in (
            rows[:5] + [r for r in shown if r not in rows[:5]]):
        note = showcased.get(ref, "")
        flag = ("  ON FRAME AT SPAWN" if off < 0 else
                "  NOT IN FRAME WHEN IT LANDS" if ref in showcased and inside < 0 else "")
        print(f"    {ref:6s} {start:6d} {land:5d} {sector:4.0f} {off:10.2f} {grew:5.2f} "
              f"{inside:8.2f}  {note}{flag}")
    print(f"    {len(entries) - len(popped)}/{len(entries)} parts are clear of the frame on "
          f"the frame they appear (worst {min(r[1][3] for r in rows):+.2f}); "
          f"biggest entry stretch x{max(r[1][4] for r in rows):.2f}")
    if popped:
        print(f"    WARNING: {len(popped)} part(s) appear inside open frame: "
              f"{', '.join(r[0] for r in popped[:8])}")
    if hidden:
        print(f"    WARNING: {', '.join(r[0] for r in hidden)} land outside the frame, and the "
              f"storyboard says they are the subject")


def print_plan(rig: Rig, cam: Camera, end: int, floor_z: float, subwaves, hero_sched,
               heroes, parts, hull=None, aspect=16 / 9, entries=None, showcased=None,
               silhouettes=True):
    print(f"\n  timeline: {end} frames, {end / FPS:.2f} s at {FPS} fps")
    print(f"    copper        1 - {F_COPPER_END}")
    print(f"    etch top     {F_ETCH_TOP[0]} - {F_ETCH_TOP[1]}   "
          f"bottom {F_ETCH_BOT[0]} - {F_ETCH_BOT[1]}")
    print(f"    mask films   {F_FILM_FLY} - {F_FILM_CONTACT[1]}   handoff +{F_HANDOFF}")
    print(f"    pads/plate   {F_PADS[0]} - {F_PADS[1]}   silkscreen {F_SILK[0]} - "
          f"{F_SILK[1]}")
    for label, j, sector, band, first, last in subwaves:
        print(f"    {label:10s} wave {j + 1}  {first:4d}-{last:4d}  sector {sector:4d}  "
              f"{len(band):3d}  {', '.join(band[:7])}{' ...' if len(band) > 7 else ''}")
    for name, (start, land, _m) in hero_sched.items():
        val = next(p["value"] for p in parts if p["ref"] == heroes[name])
        print(f"    hero {name:6s} {start:4d} -> {land:4d}   {heroes[name]} ({val})")

    print("\n  camera / board, at the probe frames")
    print("    frame    orb   az_w   el  width  radius   camz  facing  cam d/dt  "
          "board d/dt  target")
    prev, worst_rate, worst_clear, min_facing = None, 0.0, 1e9, 1.0
    stillest = (1e9, 0)
    for frame in range(1, end + 1):
        st = cam.state(frame)
        rate = 0.0
        if prev is not None:
            rate = math.degrees((st["loc"] - st["aim"]).normalized().angle(
                (prev["loc"] - prev["aim"]).normalized())) * FPS
        worst_rate = max(worst_rate, rate)
        # "Visibly moving" is the camera *or* the board: a camera that pauses over a board
        # still turning at 20 deg/s is not a static shot. Tracked separately from the peak,
        # because the failure this catches is a dead frame, not a whip.
        # Excludes the finale, whose slowness is the point. What this is hunting for is dead
        # air in the body of the piece, where a still frame would be a fault.
        if prev is not None and frame < end - 60:
            board = math.hypot(rig.yaw(frame) - rig.yaw(frame - 1),
                               rig.roll(frame) - rig.roll(frame - 1)) * FPS
            stillest = min(stillest, (rate + board, frame))
        worst_clear = min(worst_clear, st["loc"].z - floor_z)
        facing = board_facing(rig, st, frame)
        min_facing = min(min_facing, facing)
        if frame in PROBE_FRAMES or frame == end:
            d = st["loc"] - st["aim"]
            i = max(0, min(bisect.bisect_right(cam.t_frames, frame) - 1,
                           len(cam.t_names) - 1))
            board_rate = math.hypot(abs(rig.yaw(frame) - rig.yaw(frame - 1)),
                                    abs(rig.roll(frame) - rig.roll(frame - 1))) * FPS
            # `orb` is what the table authored and az_w is what came out of the scene;
            # they must differ by exactly the board's yaw, which makes the pair a check on
            # the follow rather than two ways of printing the same number.
            print(f"    {frame:5d} {st['orb']:6.1f} "
                  f"{math.degrees(math.atan2(d.x, -d.y)):6.1f} "
                  f"{st['el']:4.0f} {st['width']:6.0f} {st['radius'] * 1000:7.1f} "
                  f"{st['loc'].z * 1000:6.1f}  {facing:+.2f}  {rate:7.1f}   "
                  f"{board_rate:8.1f}   {cam.t_names[i]}")
        prev = st
    peak_board = max(math.hypot(rig.yaw(f) - rig.yaw(f - 1), rig.roll(f) - rig.roll(f - 1))
                     * FPS for f in range(2, end + 1))
    print(f"    peak camera angular rate {worst_rate:.1f} deg/s; "
          f"peak board rate {peak_board:.1f} deg/s; "
          f"min floor clearance {worst_clear * 1000:.1f} mm")
    print(f"    stillest frame (excluding the last 2 s): {stillest[1]} at "
          f"{stillest[0]:.1f} deg/s of camera+board motion")

    # Which face is presented is the entire question through fabrication, and one number per
    # camera beat is too coarse to tune it: the top etch needs the top held, the bottom etch
    # needs the underside really round, and the films need the board close to edge-on so
    # both of them read as arriving at once.
    print("    facing through fabrication (+ top, - bottom, 0 edge-on):")
    for lo in range(F_ETCH_TOP[0], 890, 180):
        cells = "  ".join(f"{f}:{board_facing(rig, cam.state(f), f):+.2f}"
                          for f in range(lo, min(lo + 180, 890), 30))
        print(f"      {cells}")
    print(f"    most-negative facing {min_facing:+.2f} "
          f"(needs < -0.35 to show the underside)")

    if entries:
        print_entries(entries, showcased or {}, silhouettes)

    if hull:
        print("    frame coverage of the whole assembly (1.00 = touching the frame edge):")
        cells = []
        for frame in (1524, 1720, 1912, 2060, 2140, 2250, 2320, 2390, 2455, end):
            h, v = frame_coverage(cam, rig, frame, hull, aspect)
            flag = "  CLIPPED" if max(h, v) > 1.0 else ""
            cells.append(f"{frame}: h {h:.2f} v {v:.2f}{flag}")
        for i in range(0, len(cells), 3):
            print("      " + "   ".join(cells[i:i + 3]))
    if worst_clear < 0.005:
        print("    WARNING: the camera comes within 5 mm of the backdrop plane")
    if min_facing > -0.35:
        print("    WARNING: the bottom copper is never presented to the camera")
    if peak_board > 16.0:
        print(f"    WARNING: board rotation peaks at {peak_board:.0f} deg/s -- at shutter "
              f"{SHUTTER} that smears routing")


# ----------------------------------------------------------------------------------- main


def read_bounds(pcb3d: Path) -> dict:
    with zipfile.ZipFile(pcb3d) as z:
        return tomllib.loads(z.read("layers/bounds.toml").decode())


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb3d", type=Path, required=True)
    ap.add_argument("--parts", type=Path, required=True, help="components.json")
    ap.add_argument("--blend", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("out/anim"))
    ap.add_argument("--width", type=int, default=2560)
    ap.add_argument("--height", type=int, default=1440)
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--light-strength", type=float, default=0.60)  # purple, calibrated
    ap.add_argument("--frames", default="all",
                    help="'all', 'a-b', a comma list of single frames, or 'probe'")
    ap.add_argument("--no-motion-blur", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--plan-only", action="store_true",
                    help="evaluate the schedule, rig and camera and print the diagnostics "
                         "without importing the board -- seconds, not minutes")
    args = ap.parse_args(argv)

    data = json.loads(args.parts.read_text(encoding="utf-8-sig"))
    parts = [p for p in data["parts"] if p["models"] and not p["dnp"]]
    bounds = read_bounds(args.pcb3d)
    size_mm = tuple(bounds["size"])
    print(f"{args.parts.name}: {len(parts)} placed footprints from {data['board']} "
          f"(KiCad {data['kicad']}), layer bounds {size_mm[0]} x {size_mm[1]} mm")

    heroes = resolve_heroes(parts)
    pos_mm, order_key = order_key_factory(parts)
    refs = [p["ref"] for p in parts]
    groups = group_parts(refs, parts, heroes, order_key)
    plan, subwaves = wave_schedule(groups, parts, order_key)
    # The three heroes get their own entrances and must not also arrive in a wave. group_parts
    # removes them before grouping, so this can only fail if a GROUP_TEST is widened to catch
    # one -- which is exactly the edit that would do it silently.
    intruders = sorted(set(plan) & set(heroes.values()))
    if intruders:
        sys.exit(f"hero(es) {intruders} are scheduled in a supporting wave as well")
    after_waves = max(land for _s, land, _sec, _sp in plan.values())
    hero_sched, after_heroes = hero_schedule(after_waves)
    end = int(CAM_BEATS[-1][0])
    if after_heroes + F_MIN_TAIL > end:
        sys.exit(f"the Teensy lands on {after_heroes} but the camera table ends on {end}: "
                 f"the finale needs at least {F_MIN_TAIL} frames")
    # Every flight in one dict, heroes included, so the schedule has a single home for both
    # the plan and the keying.
    flights = dict(plan)
    for name, (start, land, spec) in hero_sched.items():
        flights[heroes[name]] = (start, land, spec["sector"], spec)
    # The parts the storyboard promises the viewer will see arrive, which are the only ones
    # held to being in frame when they land.
    showcased = {r: f"hero {n}" for n, r in heroes.items()}
    for label in SUBJECT_GROUPS:
        for r in groups.get(label) or []:
            showcased[r] = f"subject '{label}'"

    if args.plan_only:
        # Board-local positions straight from the board file: the plan has to be evaluable
        # before anything is imported, which is the whole point of this mode.
        bx, by = bounds["top_left"]
        w, h = size_mm
        cx, cy = bx + w / 2.0, -(by + h / 2.0)
        pos_local = {r: Vector(((pos_mm[r][0] - cx) / 1000.0,
                                (pos_mm[r][1] - cy) / 1000.0, 0.004)) for r in refs}
        rig = Rig(Vector((0.0, 0.0, 0.0)))
        named = {n: pos_local[r] for n, r in heroes.items()}
        named.update(group_targets(groups, pos_local))
        cam = Camera(rig, build_targets(named, plan, pos_local, size_mm, end))
        # Centres, not silhouettes -- part extents come from the scene. Weaker, and still
        # enough to have caught both of draft 2's framing faults. Same jitter draw as the
        # render, so these are the flights that will be keyed rather than an average of them.
        rng, entries = random.Random(SEED), {}
        for ref, (start, land, sector, spec) in sorted(flights.items()):
            jitter = (rng.uniform(-12, 12), rng.uniform(-0.10, 0.10),
                      rng.uniform(-0.12, 0.12), rng.uniform(-0.25, 0.25))
            entry = entry_basis(rig, cam, start, land, pos_local[ref], spec, sector, jitter,
                                corners_local=[pos_local[ref]],
                                aspect=args.width / args.height)
            spawn = flight_world(rig, entry, Matrix.Translation(pos_local[ref]),
                                 Matrix.Identity(4), pos_local[ref], start, start, land,
                                 spec, jitter).translation
            aspect = args.width / args.height
            entries[ref] = (start, land, sector,
                            silhouette_frame(cam, start, [spawn], aspect)[1], entry["grew"],
                            silhouette_frame(cam, land, [rig.to_world(land, pos_local[ref])],
                                             aspect)[0])
        print_plan(rig, cam, end, -0.0008 - FLOOR_DROP_MM / 1000.0, subwaves, hero_sched,
                   heroes, parts, aspect=args.width / args.height, entries=entries,
                   showcased=showcased, silhouettes=False)
        return 0

    # ------------------------------------------------------------------ build the scene
    print(f"\nbuilding assembly animation v2 from {args.pcb3d.name}")
    studio.reset_scene()
    objects = studio.import_pcb3d(args.pcb3d, 1016.0, "RASTERIZED")
    studio.fix_imported_normals(objects, 30.0)
    studio.restyle_components(objects)

    board = [o for o in objects if o.name.startswith("PCB")]
    joints_by_ref, components = {}, []
    for obj in objects:
        if obj in board or obj.type != "MESH":
            continue
        if obj.name.startswith("SOLDER_"):
            # SOLDER_<value>_<ref>_<i>_<j>, from the exporter's pad naming.
            m = re.search(r"_([A-Za-z]+\d+)_(\d+)_(\d+)$", obj.name)
            if m:
                joints_by_ref.setdefault(m.group(1), []).append(obj)
            continue
        components.append(obj)
    print(f"  {len(board)} board object(s), {len(components)} component instances, "
          f"{sum(len(v) for v in joints_by_ref.values())} solder joints")
    if len(board) != 1:
        sys.exit(f"expected exactly one board object, got {[b.name for b in board]}")
    board_obj = board[0]
    if max(abs(v) for v in board_obj.rotation_euler) > 1e-6 or \
            (board_obj.scale - Vector((1, 1, 1))).length > 1e-6:
        sys.exit(f"{board_obj.name} is rotated or scaled; the rig assumes it is not")

    matched = match_objects(components, parts, recover_offset(components, parts))
    by_ref = {}
    for obj in components:
        by_ref.setdefault(matched[obj.name], []).append(obj)
    missing = (set(plan) | set(heroes.values())) - set(by_ref)
    if missing:
        sys.exit(f"scheduled parts with no objects in the scene: {sorted(missing)}")
    unscheduled = set(by_ref) - set(plan) - set(heroes.values())
    if unscheduled:
        sys.exit(f"parts with objects but no slot in the schedule: {sorted(unscheduled)}")

    lo, hi = studio.world_bbox(objects)
    board_lo, board_hi = studio.world_bbox(board)
    lights = studio.build_lighting(lo, hi, args.light_strength)
    floor = studio.build_backdrop(lo, hi, FLOOR_DROP_MM)
    riders = build_riders(args.light_strength, (hi - lo).length)
    studio.configure_render(args.width, args.height, args.samples, not args.cpu)
    studio.apply_look(lights, LOOK)
    studio.set_backdrop(floor, BACKDROP)

    # --------------------------------------------------------------------------- the rig
    centre = (board_lo + board_hi) * 0.5
    rig = Rig(centre)
    rig_obj = bpy.data.objects.new("BOARD_RIG", None)
    rig_obj.empty_display_size = 0.02
    bpy.context.scene.collection.objects.link(rig_obj)
    rig_obj.location = centre
    bpy.context.view_layer.update()

    fab = Fabrication(board_obj.data.materials[0], size_mm)
    films = build_films(board_obj, fab.images["Mask"], size_mm, fab.mask_color,
                        fab.mask_roughness)
    print(f"  film colour from the board's own solder mask: linear "
          f"{tuple(round(v, 3) for v in fab.mask_color)}, roughness {fab.mask_roughness}")

    # Where every part sits *on the board*, captured before the rig exists. This is the
    # invariant the finished animation has to reproduce, and it is board-relative on purpose:
    # unlike a basis-against-itself comparison it cannot be satisfied by a parenting mistake.
    on_board = {obj.name: (obj.matrix_parent_inverse @ obj.matrix_basis).copy()
                for obj in [*components, *(o for v in joints_by_ref.values() for o in v)]}
    board_box = (Vector(board_obj.bound_box[0]), Vector(board_obj.bound_box[6]))

    # ONLY the board and the films go onto the rig. The importer parents all 519 components
    # and solder joints to the board object, and that object is what carries the centring
    # transform -- so re-parenting a component to the rig while keeping its basis silently
    # moves it by the board's own offset, half a board in x and in y. That shipped in the
    # first draft: every part sat outside the outline. Leave the chain alone; rotate the board.
    for obj in [board_obj, *(f["obj"] for f in films.values())]:
        obj.parent = rig_obj
        obj.matrix_parent_inverse = rig_obj.matrix_world.inverted()
    bpy.context.view_layer.update()

    # Everything the solver needs, captured now: once the rig carries keyframes, reading a
    # matrix_world means asking the depsgraph what frame it thinks it is on, and it is on
    # frame 1 while the solver is asking about frame 700.
    animated = [board_obj, *components, *(o for v in joints_by_ref.values() for o in v),
                *(f["obj"] for f in films.values())]
    landed = {obj.name: (obj.matrix_basis.copy(), tuple(obj.location),
                        tuple(obj.rotation_euler), tuple(obj.scale)) for obj in animated}

    # `pre` is everything between the rig and an object's own basis, so that
    # matrix_world = rig.matrix(f) @ pre @ basis. It is constant because the rig is the only
    # thing whose transform is not authored here.
    board_local = board_obj.matrix_parent_inverse @ board_obj.matrix_basis
    pre = {}
    for obj in animated:
        if obj.parent is rig_obj:
            pre[obj.name] = obj.matrix_parent_inverse.copy()
        elif obj.parent is board_obj:
            pre[obj.name] = board_local @ obj.matrix_parent_inverse
        else:
            sys.exit(f"{obj.name} hangs off "
                     f"{obj.parent.name if obj.parent else None}, which the solver "
                     f"does not model")

    local_of, top_of, box_of, hull = {}, {}, {}, []
    for obj in [board_obj, *components]:
        hull += [pre[obj.name] @ landed[obj.name][0] @ Vector(c) for c in obj.bound_box]
    for ref, objs in by_ref.items():
        pts = [pre[obj.name] @ landed[obj.name][0] @ Vector(c)
               for obj in objs for c in obj.bound_box]
        lo_p = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi_p = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        local_of[ref] = (lo_p + hi_p) * 0.5
        top_of[ref] = hi_p.z
        # The part's own extent, which is what the entry solve needs: the eight corners of
        # this box, board-relative, so a flight can be asked where the whole silhouette is
        # rather than where its centre is.
        box_of[ref] = [Vector((x, y, z)) for x in (lo_p.x, hi_p.x)
                       for y in (lo_p.y, hi_p.y) for z in (lo_p.z, hi_p.z)]

    # Aim a little above a hero, not at its pads: at these focal lengths, aiming at the pads
    # puts the part in the lower half of the frame.
    heroes_local = {n: Vector((local_of[r].x, local_of[r].y, top_of[r] + 0.004))
                    for n, r in heroes.items()}
    subjects = dict(heroes_local)
    subjects.update(group_targets(groups, local_of, top_of))
    cam = Camera(rig, build_targets(subjects, plan, local_of, size_mm, end))

    for frame in range(1, end + 1):
        yaw, roll = rig.euler(frame)
        rig_obj.rotation_euler = (math.radians(roll), 0.0, math.radians(yaw))
        rig_obj.keyframe_insert("rotation_euler", frame=frame)
    set_interp(rig_obj, "rotation_euler", interp="LINEAR")

    # -------------------------------------------------------------------- fabrication
    # The paste front spans the whole populated phase, from just before the first part sets
    # off to just after the last one lands. Derived, not typed: it was a literal 404 here,
    # which is a copy of WAVES[0]'s start frame and would have silently gone stale the first
    # time the waves were retimed.
    fab.keyframe((WAVES[0][1]["start"] - 8, after_waves + 6))
    animate_films(films)

    # ----------------------------------------------------------------------- the camera
    cam_data = bpy.data.cameras.new("CAM_ANIM")
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.dof.use_dof = True
    cam_obj = bpy.data.objects.new("CAM_ANIM", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    focus = bpy.data.objects.new("TARGET", None)
    focus.empty_display_size = 0.01
    bpy.context.scene.collection.objects.link(focus)
    cam_data.dof.focus_object = focus

    prev_euler = None
    for frame in range(1, end + 1):
        st = cam.state(frame)
        cam_obj.location = st["loc"]
        # Euler continuity matters here: an unreferenced conversion can flip a channel by
        # 2*pi between two frames, and with linear keys that is a full spin in one frame.
        prev_euler = st["quat"].to_euler("XYZ", prev_euler) if prev_euler \
            else st["quat"].to_euler()
        cam_obj.rotation_euler = prev_euler
        focus.location = st["aim"]
        cam_data.lens = st["lens"]
        cam_data.dof.aperture_fstop = st["fstop"]
        cam_obj.keyframe_insert("location", frame=frame)
        cam_obj.keyframe_insert("rotation_euler", frame=frame)
        focus.keyframe_insert("location", frame=frame)
        cam_data.keyframe_insert("lens", frame=frame)
        cam_data.dof.keyframe_insert("aperture_fstop", frame=frame)
    for holder in (cam_obj, focus, cam_data):
        for fc in fcurves_of(holder):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"  # the path is already smooth; don't overshoot

    bake_lights(lights, riders, rig, cam, heroes_local, (hi - lo).length, end)

    # -------------------------------------------------------------------- the components
    rng = random.Random(SEED)
    keys, entries = 0, {}
    for ref, (start, land, sector, spec) in sorted(flights.items()):
        objs = by_ref[ref]
        jitter = (rng.uniform(-12, 12), rng.uniform(-0.10, 0.10),
                  rng.uniform(-0.12, 0.12), rng.uniform(-0.25, 0.25))
        centroid = local_of[ref]
        entry = entry_basis(rig, cam, start, land, centroid, spec, sector, jitter,
                            corners_local=box_of[ref], aspect=args.width / args.height)
        # Both ends of the flight, measured the same way: off frame when it appears, in frame
        # when it lands. The second one is the connector's fault stated as a number -- J8's
        # silhouette used to land 0.6 of a half-frame outside the right edge.
        land_inside = silhouette_frame(cam, land, [rig.to_world(land, p) for p in box_of[ref]],
                                       args.width / args.height)[0]
        entries[ref] = (start, land, sector, entry["clear"], entry["grew"], land_inside)
        prev = {}
        for frame in range(start, land):
            for obj in objs:
                world = flight_world(rig, entry, landed[obj.name][0], pre[obj.name],
                                     centroid, frame, start, land, spec, jitter)
                loc, quat, scale = rig.basis(frame, world, pre[obj.name]).decompose()
                prev[obj.name] = quat.to_euler("XYZ", prev[obj.name]) if obj.name in prev \
                    else quat.to_euler()
                obj.location, obj.rotation_euler, obj.scale = loc, prev[obj.name], scale
                obj.keyframe_insert("location", frame=frame)
                obj.keyframe_insert("rotation_euler", frame=frame)
                keys += 2
        # The land frame is written from the stored floats, not from the solver: this is
        # what makes the finished board bit-identical to the import.
        for obj in objs:
            _b, loc, euler, scale = landed[obj.name]
            obj.location, obj.rotation_euler, obj.scale = loc, euler, scale
            obj.keyframe_insert("location", frame=land)
            obj.keyframe_insert("rotation_euler", frame=land)
            for path in ("location", "rotation_euler"):
                set_interp(obj, path, interp="LINEAR")
            key_visibility(obj, start)

    # Solder joints belong to the part above them, so they appear when it lands: a fillet on
    # a bare pad with nothing on it looks like a defect.
    orphan = 0
    for ref, objs in joints_by_ref.items():
        if ref not in flights:
            orphan += 1
            continue
        for obj in objs:
            key_visibility(obj, flights[ref][1])
    print(f"  keyframed {len(flights)} logical parts ({keys} flight keys)"
          + (f", {orphan} designator(s) with joints but no part animation" if orphan else ""))

    # ------------------------------------------------------------------- render settings
    scene = bpy.context.scene
    scene.camera = cam_obj
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, end
    scene.render.use_motion_blur = not args.no_motion_blur
    scene.render.motion_blur_shutter = SHUTTER
    scene.render.use_persistent_data = True   # keep the BVH between frames
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str((args.outdir / "frame_").resolve())

    # ------------------------------------------------------------------- verification
    scene.frame_set(end)
    bpy.context.view_layer.update()

    # Board-relative, against what the import said, and *not* against a basis this script
    # captured after touching the parent chain. The earlier version of this check compared
    # each part's basis with a copy of itself taken after re-parenting, so it read 0.0 while
    # every part sat half a board off the outline. A check that cannot fail is not a check.
    board_inv = board_obj.matrix_world.inverted()
    worst = (0.0, None)
    for obj in [*components, *(o for v in joints_by_ref.values() for o in v)]:
        want, got = on_board[obj.name], board_inv @ obj.matrix_world
        d = max(abs(a - b) for ra, rb in zip(want, got) for a, b in zip(ra, rb))
        if d > worst[0]:
            worst = (d, obj.name)
    print(f"\n  on-board transform check at frame {end}, relative to the board: "
          f"worst |delta| {worst[0]:.3e} ({worst[1]})")
    if worst[0] > 1e-6:
        sys.exit("a part does not sit where the imported board put it")

    # Gross-misplacement guard. Independent of the transform check above, and phrased the way
    # the failure was actually spotted: is every part inside the board outline? Connectors
    # legitimately overhang, so the tolerance is generous -- this is here to catch a part
    # sitting half a board away, not to police a 2 mm overhang.
    blo, bhi = board_box
    over = []
    for obj in components:
        p = (board_inv @ obj.matrix_world).translation
        dx = max(blo.x - p.x, p.x - bhi.x, 0.0)
        dy = max(blo.y - p.y, p.y - bhi.y, 0.0)
        if max(dx, dy) > 0.012:
            over.append((max(dx, dy) * 1000, obj.name))
    span = ((bhi.x - blo.x) * 1000, (bhi.y - blo.y) * 1000)
    print(f"  outline guard: board {span[0]:.1f} x {span[1]:.1f} mm, "
          f"{len(components) - len(over)}/{len(components)} component origins inside it "
          f"(12 mm overhang allowed)")
    if over:
        for d, name in sorted(over, reverse=True)[:8]:
            print(f"    OUTSIDE by {d:7.1f} mm: {name}")
        sys.exit(f"{len(over)} component(s) are not on the board")

    print_plan(rig, cam, end, floor.location.z, subwaves, hero_sched, heroes, parts,
               hull=hull, aspect=args.width / args.height, entries=entries,
               showcased=showcased)

    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        print(f"  saved {args.blend}")
    if args.no_render:
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    frames = args.frames
    if frames == "probe":
        frames = ",".join(str(f) for f in PROBE_FRAMES + (end,))
        (args.outdir / "labels.txt").write_text(
            "\n".join(f"{f} {text}" for f, text in PROBES + ((end, "final hero, drifting"),)),
            encoding="utf-8")
    print(f"  rendering {frames} at {args.width}x{args.height}, {args.samples} samples, "
          f"{FPS} fps, shutter {SHUTTER}")
    if frames == "all":
        bpy.ops.render.render(animation=True)
    elif "-" in frames:
        a, b = (int(v) for v in frames.split("-"))
        scene.frame_start, scene.frame_end = a, b
        bpy.ops.render.render(animation=True)
    else:
        for f in (int(v) for v in frames.split(",")):
            scene.frame_set(f)
            scene.render.filepath = str((args.outdir / f"frame_{f:04d}").resolve())
            bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
