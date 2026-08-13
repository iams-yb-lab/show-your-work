"""Build a studio-lit Blender scene from a .pcb3d and render presentation stills.

Run headless (see render.ps1 for the wrapper):

    blender --background --factory-startup --python blender_scene.py -- \
        --pcb3d out/pcb_black.pcb3d --blend out/pcb_black.blend --outdir out --shot all

Everything the render depends on is built here, so the .blend it saves is reproducible:
delete it, re-run, get the same scene. Open that .blend to adjust things by hand -- the
objects you'll want are named for it:

    PCB / PCB_*            the imported board and its components
    KEY / FILL / RIM / TOP the four studio lights
    BACKDROP               the floor plane
    FOCUS                  empty the camera's depth-of-field focuses on
    CAM_hero, CAM_top, ... one camera per shot

Scene units are metres and the importer centres the board on the origin, so a 163 mm
board is 0.163 m wide. Light sizes and camera distances are all derived from the board's
measured bounding box rather than hardcoded, so this works on any board.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import addon_utils
import bpy
from mathutils import Vector

ADDON = "bl_ext.user_default.pcb3d_importer"

# Lighting looks. Multipliers on the four studio lights, so a look changes the character
# of the light without disturbing the calibrated overall exposure much.
#   even     flat and open -- nothing hidden in shadow, every trace and part legible
#   product  the default studio ratio: clear modelling, still bright
#   dramatic key almost alone plus a hard rim; deep shadows, high contrast
#   clean    low contrast and neutral, the datasheet-cover look
LOOKS = {
    "even": dict(KEY=0.59, FILL=0.53, RIM=0.34, TOP=0.66),
    "product": dict(KEY=1.00, FILL=0.30, RIM=0.60, TOP=0.35),
    # The cinematic camera looks in from the key's side at a grazing angle, so a strong key
    # blows a specular pool across the mask and floor. Chasing that down to KEY=0.30 with
    # RIM=2.10 fixed the blowout but went too far the other way -- the board went nearly
    # unreadable. These values sit between: still clearly moody and rim-led, but the parts
    # read. Draft-check before committing a long run; this balance is the fiddly one.
    "dramatic": dict(KEY=0.62, FILL=0.20, RIM=1.25, TOP=0.22),
    "clean": dict(KEY=1.00, FILL=0.45, RIM=0.40, TOP=0.55),
}

# Shot definitions. azimuth/elevation are degrees: azimuth 0 looks along -Y at the board's
# front edge, positive swings right; elevation 90 is straight down. `fill` is the fraction
# of frame the board spans (>1 crops in). `roll` tilts the camera about its view axis --
# a couple of degrees is enough to stop a shot feeling like a CAD screenshot. `pan` shifts
# the framing off-centre in fractions of the half-frame, for composition.
SHOTS = {
    # For slides: transparent, barely tilted so the layout reads almost like the top view
    # but still three-dimensional, no depth of field so every trace stays sharp.
    "slide": dict(azimuth=15, elevation=57, lens=100, fill=0.95, ortho=False,
                  dof=False, look="even", backdrop="none"),
    # Cinematic: low, long, wide open, board pushed off-centre and lit almost entirely by
    # key plus rim.
    "cinematic": dict(azimuth=-41, elevation=13, lens=135, fill=1.06, ortho=False,
                      dof=True, fstop=4.0, look="dramatic", backdrop="dark",
                      roll=-2.5, pan=(0.10, 0.13)),
    # Showcase: the interesting angle. Steeper azimuth throws the board diagonally across
    # frame, tighter crop, strong key-to-fill for real modelling on the components.
    "showcase": dict(azimuth=54, elevation=24, lens=105, fill=0.97, ortho=False,
                     dof=True, fstop=8.0, look="product", backdrop="dark", roll=2.5),
    # Official demo: square-on three-quarter product shot on a bright neutral sweep.
    "demo": dict(azimuth=-23, elevation=34, lens=85, fill=0.90, ortho=False,
                 dof=True, fstop=11.0, look="clean", backdrop="light"),
    # Extras, kept because they are useful for documentation.
    "top": dict(azimuth=0, elevation=90, lens=85, fill=0.97, ortho=True,
                dof=False, look="even", backdrop="none"),
    "detail": dict(azimuth=48, elevation=22, lens=135, fill=2.15, ortho=False,
                   dof=True, fstop=6.0, look="product", backdrop="dark"),
    # Diagnostic, not a presentation shot: frames the Teensy's micro-USB shell alone with no
    # depth of field, because that is the only way to judge crease shading on thin sheet
    # metal. `detail` cannot do this job -- it puts the shell in the corner and blurs it.
    # The shell measures x -3.9..1.5, y -8.2..-0.9, z 6.6..7.5 mm and opens towards -x, so
    # the camera sits on that side and looks slightly down across the bends.
    "usb": dict(azimuth=-115, elevation=34, lens=110, fill=0.85, ortho=False,
                dof=False, look="product", backdrop="dark",
                target_mm=((-13.0, -15.0, 0.5), (11.0, 5.0, 10.0))),
}

DEFAULT_SHOTS = "slide,cinematic,showcase,demo"

BACKDROPS = {
    # A graded environment rather than a flat one: the floor carries a soft pool of light
    # centred under the board and falling to near-black, and the world runs from almost
    # nothing at the horizon to a cool lift overhead. Both are slightly blue, which is what
    # makes it read as atmosphere instead of as grey -- a purple mask sitting in a neutral
    # void looks like a screenshot, and the same board in a cool room looks photographed.
    # Values are the same order of magnitude as `dark`, so exposure carries over.
    "mood": None,  # built by build_mood_floor / set_world_gradient, not by set_backdrop
    # floor base colour, floor roughness, world colour, world strength.
    # Roughness is deliberately high: at the grazing angles the low and hero cameras use,
    # Fresnel makes a smooth floor throw a blown-out specular hotspot behind the board
    # that competes with the subject. 0.42 spreads it into a soft pool instead.
    # A bright sweep also acts as a huge bounce card, so its world strength is kept low --
    # otherwise the ambient it adds flattens the board's own contrast.
    "dark": ((0.020, 0.021, 0.026, 1.0), 0.42, (0.021, 0.023, 0.028), 0.55),
    "light": ((0.255, 0.257, 0.264, 1.0), 0.50, (0.150, 0.154, 0.163), 0.95),
}


# ---------------------------------------------------------------- scene teardown/import


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights):
        for item in list(block):
            block.remove(item)


def import_pcb3d(path: Path, texture_dpi: float, pcb_material: str) -> list[bpy.types.Object]:
    addon_utils.enable(ADDON, default_set=False, persistent=True)
    before = set(bpy.data.objects)
    bpy.ops.pcb2blender.import_pcb3d(
        filepath=str(path),
        import_components=True,
        add_solder_joints="SMART",
        center_boards=True,
        cut_boards=True,
        stack_boards=True,
        merge_materials=True,
        enhance_materials=True,
        pcb_material=pcb_material,
        texture_dpi=texture_dpi,
        import_fpnl=False,
    )
    imported = [o for o in bpy.data.objects if o not in before]
    if not imported:
        sys.exit("import produced no objects")
    return imported


def fix_imported_normals(objects, angle_deg: float) -> int:
    """Re-derive shading sharpness from geometry instead of trusting the STEP -> VRML normals.

    KiCad writes a creaseAngle into the VRML it hands Blender, and the importer turns that
    into custom split normals with every polygon flagged smooth. Chunky plastic survives
    that; thin sheet metal with tight bends does not -- the Teensy's micro-USB shell ends up
    shaded across creases that are genuinely sharp and reads like crumpled foil.

    Only meshes actually carrying custom normals are touched, which is exactly the set that
    came through the STEP conversion. The board itself is generated by pcb2blender from
    polygons and has none, so it is left alone.

    shade_smooth_by_angle (4.1+) is the right operator here, not shade_auto_smooth: the
    latter adds a "Smooth by Angle" geometry-nodes modifier pulled from the essentials asset
    library, which is not a safe bet under --factory-startup. This one writes sharp-edge
    flags straight into the mesh.
    """
    if angle_deg <= 0:
        print("  normals: left as imported (--smooth-angle 0)")
        return 0
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # Components arrive as linked duplicates sharing mesh data, and both operators below act
    # on the mesh, so dedupe by datablock -- otherwise the same fix runs a dozen times.
    candidates, seen = [], set()
    for obj in objects:
        if obj.type != "MESH" or obj.data.name in seen or not obj.data.has_custom_normals:
            continue
        seen.add(obj.data.name)
        candidates.append(obj)
    if not candidates:
        print("  normals: no custom split normals found, nothing to fix")
        return 0

    fixed = 0
    for obj in candidates:
        try:
            was_hidden, was_hidden_vp = obj.hide_get(), obj.hide_viewport
        except RuntimeError as exc:  # not in this view layer, so no operator can reach it
            print(f"  normals: skipped {obj.name}: {exc}")
            continue
        # The operators poll for a visible, active object, and pcb2blender hides some parts.
        obj.hide_set(False)
        obj.hide_viewport = False
        try:
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
            fixed += 1
        except RuntimeError as exc:
            print(f"  normals: skipped {obj.name}: {exc}")
        finally:
            obj.hide_viewport = was_hidden_vp
            obj.hide_set(was_hidden)

    bpy.ops.object.select_all(action="DESELECT")
    print(f"  normals: re-derived on {fixed}/{len(candidates)} STEP mesh(es) "
          f"at {angle_deg:g} deg")
    return fixed


# The Teensy's own STEP model is the least realistic thing on the board, in two ways that
# have nothing to do with each other:
#
#   Colour   its soldermask is modelled as pure saturated green, linear (0, 0.497, 0), which
#            renders neon. A real Teensy is a much darker, slightly blue-green mask.
#   Material pcb2blender's enhance_materials could not infer a material family from the VRML
#            and gave every shape on it MAT4CAD_plastic-custom_*-semi_matte. The micro-USB
#            shell and the gold pads are therefore *plastic*, which no amount of fixing the
#            normals will make read as metal.
#
# Linear-Rec709 values, since Blender colour sockets are linear, not sRGB.
TEENSY_MASK = (0.015, 0.105, 0.045)      # ~#215B3C in sRGB: dark PCB green
# A fully metallic shader has no diffuse term, so it shows only what it reflects -- and this
# studio is a deliberately dark room with four smallish area lights. At metallic 1.0 the
# shell rendered nearly black. Backing metallic off and roughening the finish lets it pick up
# the broad top softbox instead of mirroring the dark world; see the finish sweep in
# RENDER-LOG.md for what each value looked like.
TEENSY_SHELL = (0.720, 0.720, 0.730)     # nickel-plated steel, satin not mirror
TEENSY_SHELL_ROUGHNESS = 0.42
TEENSY_SHELL_METALLIC = 0.85

# Two more model colours that are wrong for the parts we actually fitted, both judged against
# photographs of the real components rather than from the model.
#
# The Harting DIN 41612 body ships at linear (0.839, 0.815, 0.745), which renders near-white
# and, being the largest object in every shot, takes over the frame. Real ones are beige. Its
# recessed pin field is a separate, darker slot and is kept proportionally darker.
HARTING_BODY = (0.520, 0.440, 0.300)     # ~#BFB195 in sRGB
HARTING_SHROUD = (0.310, 0.262, 0.180)
# The Phoenix MKDS ships at linear (0.337, 0.68, 0.44) -- pale mint. The hue is right and the
# saturation is not: MKDS green is a solid medium green.
PHOENIX_GREEN = (0.055, 0.290, 0.065)    # ~#429348 in sRGB

# Which slots on which components need restyling. Rules are scoped by object name on purpose:
# a colour test alone is not safe board-wide, since the neutral light grey that means "screw
# cage" on the terminal block is white plastic on the Teensy, and the brass of a trimpot screw
# is also an LED lens elsewhere.
#
# Except for the Teensy's mask and its USB shell, these rules KEEP the model's own colour and
# change only the shading model, because "this should be metal" is a statement about the
# shader, not about what colour the part is. Selectors are defined in select_slots().
#
# The name is matched as a substring, so a rule can key on the readable part of a long
# footprint name ("HARTING" rather than the LCSC code that name happens to start with).
COMPONENT_RULES = (
    # object name     selector          action
    ("Teensy",        "green",          dict(kind="color", color=TEENSY_MASK)),
    ("Teensy",        "tallest",        dict(kind="metal", color=TEENSY_SHELL,
                                             rough=TEENSY_SHELL_ROUGHNESS,
                                             metal=TEENSY_SHELL_METALLIC)),
    ("Teensy",        "gold",           dict(kind="metal", rough=0.35, metal=0.90)),
    # The pins, not the black body: gold-flashed brass on a real header.
    ("PinHeader",     "gold",           dict(kind="metal", rough=0.35, metal=0.90)),
    # The generated 0.1" standoff the Teensy stands on (gen_teensy_headers.py). Same part,
    # same treatment as the board's own headers -- only its gold is mixed differently.
    ("PinHeader",     "warm_gold",      dict(kind="metal", rough=0.30, metal=0.92)),
    # The Bourns 3296W adjustment screw -- the round slotted head you put a driver in.
    ("3296W",         "brass",          dict(kind="metal", rough=0.38, metal=0.90)),
    # Phoenix terminal block: the screw and its cage, not the green shroud. Selected by
    # colour rather than height because the shroud is actually the taller of the two.
    ("TerminalBlock", "neutral_light",  dict(kind="metal", rough=0.40, metal=0.85)),
    # ...and then the shroud itself, to a real MKDS green. `greenish` and not `green`: the
    # model's mint has so much red and blue in it that the strict test misses it.
    ("TerminalBlock", "greenish",       dict(kind="color", color=PHOENIX_GREEN)),
    # Harting body then pin field. `pale` first, because `neutral_light` would otherwise take
    # the body too -- matched slots are removed as they are consumed, so order decides.
    ("HARTING",       "pale",           dict(kind="color", color=HARTING_BODY)),
    ("HARTING",       "neutral_light",  dict(kind="color", color=HARTING_SHROUD)),
)


def mat4cad_color(mat):
    """The Color socket of a mat4cad BSDF group, or None if this isn't one.

    Keys on the socket name rather than the node type: mat4cad registers a custom node
    (bl_idname ShaderNodeBsdfMat4cad) whose type string is not a stable thing to match on,
    and a plain Principled has "Base Color", not "Color", so this can't collide with one.
    """
    if not mat or not mat.use_nodes:
        return None
    for node in mat.node_tree.nodes:
        socket = node.inputs.get("Color")
        if socket is not None and not socket.is_linked:
            return socket
    return None


def make_metal(mat, base_color, roughness, metallic=1.0):
    """Replace a material's shader with a metallic Principled BSDF, keeping its output.

    Everything here goes through node *names*, never through held references. Blender's RNA
    wrappers have no stable Python identity -- two lookups of the same node can return
    different objects, so `node is not keeper` is not a reliable way to spare one node, and
    removing from a collection can invalidate references you are still holding. The earlier
    version of this function did exactly that and deleted the Material Output along with the
    rest, which renders the material pure black no matter what its BSDF says. That cost a
    four-way finish sweep whose tiles all came out identical.
    """
    tree = mat.node_tree
    out_name = next((n.name for n in tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
    for name in [n.name for n in tree.nodes if n.name != out_name]:
        tree.nodes.remove(tree.nodes[name])
    out = tree.nodes[out_name] if out_name else tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (out.location.x - 320, out.location.y)
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])


def select_slots(selector: str, slots: dict) -> list[int]:
    """Material slot indices on one mesh matching a named selector.

    `slots` maps slot index -> dict(color=(r,g,b), area, top), all measured from the mesh.
    Colours are linear. The ratio tests are what keep these apart:

        gold   warm near-white with real blue still in it, b/r ~ 0.6 (ENIG, gold flash)
        brass  much yellower, almost no blue, b/r ~ 0.15
        green  strongly green-dominant over both other channels
        greenish  the same but tolerant of a desaturated, milky green
        neutral_light  near-greyscale and bright: bare steel or nickel
        pale   brighter still, near-white whatever its tint

    Without the lower b/r bound on `gold`, brass parts match it too; without the upper bound,
    plain white plastic does. `pale` and `neutral_light` deliberately overlap, so a component
    wanting both must list `pale` first -- restyle_components consumes slots as it matches.
    """
    out = []
    for i, s in slots.items():
        r, g, b = s["color"]
        if selector == "green":
            ok = g > 1.6 * r + 0.02 and g > 1.6 * b + 0.02
        elif selector == "greenish":
            ok = g > r and g > b and g - max(r, b) > 0.12
        elif selector == "pale":
            ok = (r + g + b) / 3 > 0.70
        elif selector == "gold":
            ok = r > 0.6 and 0.80 < g / max(r, 1e-6) < 0.97 and 0.45 < b / max(r, 1e-6) < 0.75
        elif selector == "warm_gold":
            # Our own generated header posts are a more saturated gold than the KiCad
            # library's ENIG flash that `gold` was tuned on (0.855/0.738/0.491): they sit at
            # 0.823/0.658/0.279, which misses `gold`'s g/r floor by 0.001 and its b/r floor
            # outright. Widened here rather than by loosening `gold`, which would then start
            # catching brass.
            ok = r > 0.6 and 0.74 < g / max(r, 1e-6) < 0.92 and 0.25 < b / max(r, 1e-6) < 0.42
        elif selector == "brass":
            ok = r > 0.6 and 0.70 < g / max(r, 1e-6) < 0.90 and b / max(r, 1e-6) < 0.30
        elif selector == "neutral_light":
            ok = max(r, g, b) - min(r, g, b) < 0.08 and (r + g + b) / 3 > 0.60
        elif selector == "tallest":
            # Everything within 0.2 mm of the highest, not just the single max: a part's top
            # feature is often split across two slots that share one material, and picking
            # only the argmax would restyle half of it and leave the other half plastic.
            top = max(v["top"] for v in slots.values())
            ok = s["top"] >= top - 0.0002
        else:
            sys.exit(f"unknown selector {selector!r}")
        if ok:
            out.append(i)
    return out


def measure_slots(obj) -> dict:
    """Per-material-slot colour, surface area and highest point, measured off the mesh."""
    me = obj.data
    slots = {}
    for poly in me.polygons:
        s = slots.get(poly.material_index)
        if s is None:
            s = slots[poly.material_index] = {"area": 0.0, "top": -1e9, "color": (0.0, 0.0, 0.0)}
        s["area"] += poly.area
        s["top"] = max(s["top"], max((obj.matrix_world @ me.vertices[v].co).z
                                     for v in poly.vertices))
    for i in list(slots):
        socket = mat4cad_color(me.materials[i]) if i < len(me.materials) else None
        if socket is None:
            del slots[i]          # already restyled, or not a mat4cad material
        else:
            slots[i]["color"] = tuple(socket.default_value[:3])
    return slots


def restyle_components(objects) -> int:
    """Apply COMPONENT_RULES: real metal where the model shipped plastic, realistic mask green.

    Meshes are deduplicated by datablock, since components arrive as linked duplicates and
    restyling shared mesh data twice would be wasted work. Matched slots are copied before
    being edited: the import runs with merge_materials=True, so one material datablock is
    shared by every identically-coloured shape on the board, and editing in place would reach
    parts no rule ever looked at.
    """
    done, changed = set(), 0
    for obj in objects:
        if obj.type != "MESH" or not obj.data.materials or obj.data.name in done:
            continue
        # Generated solder fillets carry a purpose-built material from the importer, and their
        # names embed the footprint's, so a substring rule for "Teensy" reaches them and would
        # repaint every joint on the part with the USB shell's nickel.
        if obj.name.startswith("SOLDER_"):
            continue
        rules = [(sel, act) for key, sel, act in COMPONENT_RULES if key in obj.name]
        if not rules:
            continue
        done.add(obj.data.name)
        slots = measure_slots(obj)
        for sel, act in rules:
            for i in select_slots(sel, slots):
                mat = obj.data.materials[i].copy()
                obj.data.materials[i] = mat
                was = tuple(round(v, 3) for v in slots[i]["color"])
                if act["kind"] == "metal":
                    make_metal(mat, act.get("color", slots[i]["color"]),
                               act["rough"], act["metal"])
                else:
                    mat4cad_color(mat).default_value = (*act["color"], 1.0)
                changed += 1
                print(f"    {obj.name[:34]:34s} slot {i:<2d} {sel:13s} -> {act['kind']:5s} "
                      f"(was {was}, {slots[i]['area'] * 1e6:.1f} mm2)")
                # measure_slots' cached colour is now stale for this slot, and a later rule
                # must not match an already-restyled slot.
                del slots[i]
    print(f"  restyled {changed} material slot(s) across {len(done)} component mesh(es)")
    return changed


def world_bbox(objects) -> tuple[Vector, Vector]:
    # matrix_world is lazily evaluated; without this the transforms read back stale.
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objects if o.type == "MESH" for c in o.bound_box]
    if not pts:
        sys.exit("no mesh geometry to frame")
    return (
        Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
        Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))),
    )


# ------------------------------------------------------------------------------- studio


def add_area_light(name, energy, size, location, target, color=(1, 1, 1), spread=None):
    light = bpy.data.lights.new(name, type="AREA")
    light.energy = energy
    light.size = size
    light.color = color
    light.use_shadow = True
    if spread is not None:
        light.spread = math.radians(spread)
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def aim(obj, target: Vector):
    """Point an object's -Z at target (lights and cameras both look down -Z)."""
    direction = (Vector(target) - obj.location).normalized()
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_lighting(lo: Vector, hi: Vector, strength: float):
    """Four soft sources: a big key at 45 degrees, a wide fill, an edge rim, a top box.

    Sizes scale with the board diagonal -- a source has to be large relative to the
    subject to read as soft, and a light rig tuned on a 50 mm board looks harsh on a
    165 mm one.
    """
    center = (lo + hi) * 0.5
    diag = (hi - lo).length
    d = diag * 1.15  # working distance

    # Energy scales with distance^2 so exposure is invariant to board size: the bases
    # below are watts at a 0.2 m working distance, calibrated once against a measured
    # mean scene luminance (see calibrate_exposure in render.ps1's notes). Change
    # --light-strength to move all four together and keep the ratios intact.
    def watts(base):
        return base * strength * (d / 0.2) ** 2

    lights = {
        # Key: high and front-left, the source that defines component shadows.
        "KEY": add_area_light("KEY", watts(2.80), diag * 0.85,
                              center + Vector((-d * 0.75, -d * 0.60, d * 0.85)), center,
                              color=(1.0, 0.985, 0.960)),
        # Fill: broad, dim, opposite the key, lifts the shadow side without flattening.
        "FILL": add_area_light("FILL", watts(0.81), diag * 1.5,
                               center + Vector((d * 1.05, -d * 0.35, d * 0.30)), center,
                               color=(0.945, 0.965, 1.0)),
        # Rim: low and behind, skims the board edge and component tops. This is what
        # keeps a dark soldermask from disappearing into a dark background.
        "RIM": add_area_light("RIM", watts(1.71), diag * 0.55,
                              center + Vector((d * 0.30, d * 1.10, d * 0.38)), center,
                              color=(0.92, 0.955, 1.0)),
        # Top: a softbox straight overhead for even sheen across the mask.
        "TOP": add_area_light("TOP", watts(0.93), diag * 1.7,
                              center + Vector((0, 0, d * 1.5)), center),
    }
    # Remember the calibrated level so a look can scale it and still be undoable.
    for obj in lights.values():
        obj.data["base_energy"] = obj.data.energy
    return lights


def apply_look(lights: dict, look: str):
    mult = LOOKS[look]
    for name, obj in lights.items():
        obj.data.energy = obj.data["base_energy"] * mult[name]


def build_backdrop(lo: Vector, hi: Vector, float_mm: float):
    """Create the floor plane once. Per-shot appearance is set by set_backdrop()."""
    diag = (hi - lo).length
    bpy.ops.mesh.primitive_plane_add(size=diag * 14, location=(0, 0, lo.z - float_mm / 1000.0))
    floor = bpy.context.active_object
    floor.name = "BACKDROP"

    mat = bpy.data.materials.new("BACKDROP")
    mat.use_nodes = True
    floor.data.materials.append(mat)
    # Remembered here because the `mood` backdrop's pool has to scale with the board, and
    # set_backdrop() -- which is called per shot, and cannot see the bounding box -- is
    # where the gradient gets switched on.
    floor["pool_radius"] = diag * 1.05
    return floor


MOOD_POOL = (0.026, 0.028, 0.045, 1.0)      # lit floor immediately under the board
MOOD_FAR = (0.004, 0.004, 0.007, 1.0)       # the same floor, far away
MOOD_HORIZON = (0.005, 0.006, 0.011)        # world, low down
MOOD_SKY = (0.022, 0.026, 0.040)            # world, overhead
MOOD_WORLD_STRENGTH = 0.50
MOOD_ROUGHNESS = 0.50
# Tuned down twice, and the reason is worth keeping. First cut: sky 0.058 at strength 0.80,
# which lit the floor to an even mid grey and buried the pool entirely -- a clean studio, not
# an atmosphere. Second cut fixed the world but left the pool at 0.060, and under four
# calibrated studio lights a base of 0.060 renders as bright grey: the floor came out lighter
# than the board's shadow side, and the far edge of the plane read as a hard diagonal seam
# against the dark world. What makes a floor dark is its albedo, not the world above it.
# These values sit just above the flat `dark` backdrop's 0.020, so the lift near the board is
# visible while the floor still reads as a dark surface.


def build_mood_floor(floor, pool_radius: float):
    """Give the floor a radial gradient, so the board sits in a pool of light.

    Object coordinates are used rather than Generated: Generated is normalised to the
    object's bounding box, which for a plane 14 board-diagonals wide would stretch the pool
    with the board size. Object space is in metres, so dividing by `pool_radius` puts the
    gradient's unit sphere exactly where we want the falloff -- one number, in metres, that
    means the same thing on any board.
    """
    mat = floor.data.materials[0]
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]

    coord = tree.nodes.new("ShaderNodeTexCoord")
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0 / pool_radius,) * 3
    grad = tree.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    # Spherical gradient is 1 at the origin and 0 at radius 1. Two stops, with the bright
    # end pulled in to 0.55 so the pool has an edge to it instead of a smear.
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = MOOD_FAR
    ramp.color_ramp.elements[1].position = 0.34
    ramp.color_ramp.elements[1].color = MOOD_POOL

    for node, x in ((coord, -900), (mapping, -700), (grad, -520), (ramp, -340)):
        node.location = (x, 300)
    tree.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    tree.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    # High, for the same reason the flat backdrops are: at the grazing angles these cameras
    # use, a smoother floor throws a specular sheet that competes with the board and turns
    # the plane's far edge into a visible line.
    bsdf.inputs["Roughness"].default_value = MOOD_ROUGHNESS


def set_world_gradient(horizon, sky, strength: float):
    """A vertical world gradient instead of a flat colour, for a horizon to sit against."""
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    bg = tree.nodes["Background"]
    bg.inputs["Strength"].default_value = strength

    coord = tree.nodes.new("ShaderNodeTexCoord")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    rng = tree.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = -0.35
    rng.inputs["From Max"].default_value = 0.75
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*horizon, 1.0)
    ramp.color_ramp.elements[1].color = (*sky, 1.0)

    for node, x in ((coord, -900), (sep, -700), (rng, -520), (ramp, -340)):
        node.location = (x, 0)
    # Generated on a world shader is the view direction, so Z is "how far up am I looking".
    tree.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], rng.inputs["Value"])
    tree.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])


def set_backdrop(floor, kind: str):
    """Switch the floor and world between dark / bright / fully transparent.

    Hiding the floor is not enough on its own for a cut-out: film_transparent has to go on
    too, or Cycles still renders the world colour behind the board.
    """
    scene = bpy.context.scene
    if kind == "none":
        scene.render.film_transparent = True
        floor.hide_render = True
        # Keep a little ambient so the shadow side of components isn't pure black.
        set_world((0.055, 0.057, 0.062), 0.9)
        return

    scene.render.film_transparent = False
    floor.hide_render = False
    if kind == "mood":
        # Built on first use, not at scene-build time: wiring a gradient into Base Color
        # would silently disable the flat backdrops, which set that socket's value directly.
        if not floor.data.materials[0].node_tree.nodes.get("Gradient Texture"):
            build_mood_floor(floor, floor.get("pool_radius", 0.2))
        set_world_gradient(MOOD_HORIZON, MOOD_SKY, MOOD_WORLD_STRENGTH)
        return
    base_color, roughness, world_color, world_strength = BACKDROPS[kind]
    set_world(world_color, world_strength)

    bsdf = floor.data.materials[0].node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness


def set_world(color, strength):
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength


# -------------------------------------------------------------------------------- camera


def shot_box(spec, lo: Vector, hi: Vector) -> tuple[Vector, Vector]:
    """What this shot frames: the whole board, or the `target_mm` box if it declares one.

    Only framing and focus read this. The light rig is still built from the board's own
    bounding box, so a tight diagnostic crop is lit exactly like the presentation shots
    rather than by a rig scaled to a 20 mm subject.
    """
    target = spec.get("target_mm")
    if not target:
        return lo, hi
    return (Vector([v / 1000.0 for v in target[0]]),
            Vector([v / 1000.0 for v in target[1]]))


def add_camera(name, spec, lo: Vector, hi: Vector, focus, aspect: float):
    center = (lo + hi) * 0.5
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = spec["lens"]
    cam_data.type = "ORTHO" if spec["ortho"] else "PERSP"
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)

    az, el = math.radians(spec["azimuth"]), math.radians(spec["elevation"])
    direction = Vector((
        math.sin(az) * math.cos(el),
        -math.cos(az) * math.cos(el),
        math.sin(el),
    ))
    cam.location = center + direction * (hi - lo).length * 2.5
    aim(cam, center)
    # Roll before fitting, not after: rolling turns the frame relative to the board, so a
    # board that exactly fitted beforehand gets its corners pushed back outside. Doing it
    # first means the fit sees the rolled orientation and accounts for it.
    if spec.get("roll"):
        cam.rotation_euler.rotate_axis("Z", math.radians(spec["roll"]))
    # The framing maths below reads cam.matrix_world, which is only valid after the
    # depsgraph catches up with the location/rotation we just assigned.
    bpy.context.view_layer.update()

    if spec["ortho"]:
        cam_data.ortho_scale = fit_ortho(cam, lo, hi, aspect) / spec["fill"]
    else:
        fit_perspective(cam, lo, hi, aspect, spec["fill"])
        if spec.get("pan"):
            pan_camera(cam, center, aspect, *spec["pan"])

    bpy.context.view_layer.update()
    print(f"  {name}: loc {tuple(round(v, 3) for v in cam.location)}, "
          f"{'ortho ' + str(round(cam_data.ortho_scale, 3)) if spec['ortho'] else str(spec['lens']) + 'mm'}"
          f", look={spec['look']}, backdrop={spec['backdrop']}")

    if spec["dof"]:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_object = focus
        # A PCB is small, so the camera sits close and depth of field goes shallow fast:
        # f/11 holds the whole board, f/4 is a deliberately cinematic sliver.
        cam_data.dof.aperture_fstop = spec.get("fstop", 11.0)
    return cam


def pan_camera(cam, center: Vector, aspect: float, dx: float, dy: float):
    """Slide the camera sideways/up in its own plane to push the subject off-centre.

    dx/dy are fractions of the half-frame at the subject's distance, so the shift means
    the same thing regardless of lens or board size.
    """
    tan_h, tan_v = half_angles(cam, aspect)
    dist = (center - cam.location).length
    offset = Vector((dx * tan_h * dist, dy * tan_v * dist, 0.0))
    cam.location += cam.matrix_world.to_quaternion() @ offset


def corners_in_camera_space(cam, lo: Vector, hi: Vector):
    inv = cam.matrix_world.inverted()
    return [
        inv @ Vector((x, y, z))
        for x in (lo.x, hi.x)
        for y in (lo.y, hi.y)
        for z in (lo.z, hi.z)
    ]


def half_angles(cam, aspect: float) -> tuple[float, float]:
    """tan of the half field of view, horizontal and vertical."""
    d = cam.data
    sensor = d.sensor_width
    tan_h = (sensor * 0.5) / d.lens
    tan_v = tan_h / aspect
    return tan_h, tan_v


def fit_perspective(cam, lo: Vector, hi: Vector, aspect: float, fill: float):
    """Slide the camera along its own view axis until the board fits the frame.

    Translating along local Z leaves each corner's camera-space x and y untouched and
    shifts z by a constant, so the required distance solves in closed form instead of
    needing a search.
    """
    # Fitting the board to a cone of tangent t*fill leaves it spanning exactly `fill` of
    # the real frame, so fill=0.9 gives a 10% margin and fill>1 crops in. (Multiply, not
    # divide -- dividing inverts the meaning and pushes the camera away instead.)
    tan_h, tan_v = half_angles(cam, aspect)
    tan_h, tan_v = tan_h * fill, tan_v * fill
    d = max(
        max(abs(p.x) / tan_h + p.z, abs(p.y) / tan_v + p.z)
        for p in corners_in_camera_space(cam, lo, hi)
    )
    cam.location += cam.matrix_world.to_quaternion() @ Vector((0, 0, d))


def fit_ortho(cam, lo: Vector, hi: Vector, aspect: float) -> float:
    pts = corners_in_camera_space(cam, lo, hi)
    width = max(abs(p.x) for p in pts) * 2
    height = max(abs(p.y) for p in pts) * 2
    return max(width, height * aspect)


# ------------------------------------------------------------------------ render config


def configure_render(width, height, samples, use_gpu):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 15

    cy = scene.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.008
    cy.use_denoising = True
    cy.max_bounces = 16
    cy.transmission_bounces = 12
    cy.transparent_max_bounces = 16
    # Clamping indirect light kills fireflies off the gold/copper highlights, which are
    # the main source of speckle on a board render.
    cy.sample_clamp_indirect = 8.0
    cy.blur_glossy = 0.6
    cy.caustics_reflective = False
    cy.caustics_refractive = False

    if use_gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev_type in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            try:
                prefs.compute_device_type = dev_type
            except TypeError:
                continue
            prefs.get_devices()
            found = [d for d in prefs.devices if d.type == dev_type]
            if found:
                for d in prefs.devices:
                    d.use = d.type == dev_type
                cy.device = "GPU"
                cy.denoiser = "OPTIX" if dev_type == "OPTIX" else "OPENIMAGEDENOISE"
                print(f"  cycles: GPU via {dev_type} -- {found[0].name}")
                break
        else:
            print("  cycles: no GPU found, falling back to CPU")

    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "Punchy", "AgX - Medium Contrast"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue

    add_glare()


def add_glare():
    """A whisper of bloom on the specular hits -- just enough to take the hard edge off
    gold pad highlights. Overdone, this is the single fastest way to make a product
    render look cheap, so Strength stays low.

    Blender 4.4 moved the Glare node's controls from node properties onto input sockets
    and left the old properties as no-op stubs (setting node.threshold logs
    "RNA_float_set: NodeSocket.default_value not found" and changes nothing). Set the
    sockets when they exist and fall back to properties on older builds.
    """
    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    render_layers = next((n for n in tree.nodes if n.type == "R_LAYERS"), None)
    composite = next((n for n in tree.nodes if n.type == "COMPOSITE"), None)
    if not (render_layers and composite):
        return
    try:
        glare = tree.nodes.new("CompositorNodeGlare")
    except RuntimeError:
        return

    modes = {i.identifier for i in glare.bl_rna.properties["glare_type"].enum_items}
    glare.glare_type = "BLOOM" if "BLOOM" in modes else "FOG_GLOW"
    glare.quality = "HIGH"

    wanted = {"Threshold": 1.0, "Strength": 0.05, "Size": 7.0, "Smoothness": 0.25}
    for name, value in wanted.items():
        if name in glare.inputs:
            glare.inputs[name].default_value = value
        elif name == "Threshold":
            glare.threshold = value
        elif name == "Strength":
            glare.mix = -1.0 + 2.0 * value  # legacy mix: -1 = image only, +1 = glare only
        elif name == "Size":
            glare.size = int(value)

    glare.location = (render_layers.location.x + 260, render_layers.location.y)
    composite.location = (glare.location.x + 260, glare.location.y)
    tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], composite.inputs["Image"])


# ---------------------------------------------------------------------------------- main


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb3d", type=Path, required=True)
    ap.add_argument("--blend", type=Path, help="save the assembled scene here")
    ap.add_argument("--outdir", type=Path, default=Path("out"))
    ap.add_argument("--prefix", default="pcb")
    ap.add_argument("--shot", default=DEFAULT_SHOTS, help="comma separated, or 'all'")
    ap.add_argument("--backdrop", choices=["dark", "light", "none", "mood"],
                    help="override every shot's own backdrop")
    ap.add_argument("--width", type=int, default=3840)
    ap.add_argument("--height", type=int, default=2160)
    ap.add_argument("--samples", type=int, default=512)
    ap.add_argument("--light-strength", type=float, default=1.0)
    ap.add_argument("--float-mm", type=float, default=0.0,
                    help="lift the board off the floor for a softer contact shadow")
    ap.add_argument("--texture-dpi", type=float, default=1016.0)
    ap.add_argument("--smooth-angle", type=float, default=30.0,
                    help="re-derive shading sharpness above this angle; 0 keeps the "
                         "imported STEP normals (which shatter thin sheet metal)")
    ap.add_argument("--raw-materials", action="store_true",
                    help="skip COMPONENT_RULES: keep the models' own all-plastic materials "
                         "and the Teensy's neon mask")
    ap.add_argument("--pcb-material", choices=["RASTERIZED", "3D"], default="RASTERIZED")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="build and save, don't render")
    args = ap.parse_args(argv)

    shots = list(SHOTS) if args.shot == "all" else [s.strip() for s in args.shot.split(",")]
    unknown = [s for s in shots if s not in SHOTS]
    if unknown:
        return print(f"unknown shot(s) {unknown}; have {list(SHOTS)}") or 1

    print(f"building scene from {args.pcb3d.name}")
    reset_scene()
    objects = import_pcb3d(args.pcb3d, args.texture_dpi, args.pcb_material)
    fix_imported_normals(objects, args.smooth_angle)
    if not args.raw_materials:
        restyle_components(objects)
    lo, hi = world_bbox(objects)
    size_mm = tuple(round(v * 1000, 1) for v in (hi - lo))
    print(f"  imported {len(objects)} objects, bbox {size_mm[0]} x {size_mm[1]} x {size_mm[2]} mm")

    if args.float_mm:
        for o in objects:
            if not o.parent:
                o.location.z += args.float_mm / 1000.0
        lo, hi = world_bbox(objects)

    lights = build_lighting(lo, hi, args.light_strength)
    floor = build_backdrop(lo, hi, args.float_mm)

    focus = bpy.data.objects.new("FOCUS", None)
    bpy.context.scene.collection.objects.link(focus)
    focus.location = (lo + hi) * 0.5
    focus.empty_display_size = (hi - lo).length * 0.05

    configure_render(args.width, args.height, args.samples, not args.cpu)
    aspect = args.width / args.height
    cameras = {}
    for name in shots:
        spec = SHOTS[name]
        s_lo, s_hi = shot_box(spec, lo, hi)
        s_focus = focus
        if spec.get("target_mm"):
            # Board-centre focus would defocus a tight crop, so give it its own target.
            s_focus = bpy.data.objects.new(f"FOCUS_{name}", None)
            bpy.context.scene.collection.objects.link(s_focus)
            s_focus.location = (s_lo + s_hi) * 0.5
            s_focus.empty_display_size = (s_hi - s_lo).length * 0.1
        cameras[name] = add_camera(f"CAM_{name}", spec, s_lo, s_hi, s_focus, aspect)

    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        first = SHOTS[shots[0]]
        apply_look(lights, first["look"])
        set_backdrop(floor, args.backdrop or first["backdrop"])
        bpy.context.scene.camera = cameras[shots[0]]
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        print(f"  saved {args.blend} (set up as '{shots[0]}')")

    if args.no_render:
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    for name in shots:
        spec = SHOTS[name]
        out = (args.outdir / f"{args.prefix}_{name}.png").resolve()
        # Each shot carries its own lighting ratio and backdrop, so re-apply per render.
        apply_look(lights, spec["look"])
        set_backdrop(floor, args.backdrop or spec["backdrop"])
        bpy.context.scene.camera = cameras[name]
        bpy.context.scene.render.filepath = str(out)
        print(f"  rendering {name} -> {out.name} at {args.width}x{args.height}, "
              f"{args.samples} samples")
        bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
