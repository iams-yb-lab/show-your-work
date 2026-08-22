# Vendor STEP → Blender, with colours — the verified route

When the subject of a showoff render is a vendor STEP assembly (no KiCad board, so the
pcb2blender route in `../showoff/assembly/picture/README.md` does not apply), this is the
conversion and inspection chain that works. Every step below was run and verified on
Windows 11 / Blender 4.2.2 LTS / FreeCAD 0.21.2 / Mayo 0.10.0, 2026-08-17, converting the
official Red Pitaya STEMlab 125-14 model (1127 STEP products → 4412 Blender objects,
43 materials with correct per-part colours).

## The one-line summary

**Convert with `mayo-conv`, not with headless FreeCAD.** Inspect in Blender over the
Blender-lab MCP add-on.

## Step 1 — convert the STEP with Mayo

[Mayo](https://github.com/fougue/mayo) is an OCCT-based converter with a proper CLI. The
win64 binaries zip is portable — no installer, no admin rights.

```powershell
curl.exe -sL -o mayo.zip https://github.com/fougue/mayo/releases/download/v0.10.0/Mayo-0.10.0-win64-binaries.zip
Expand-Archive mayo.zip -DestinationPath mayo
mayo\Mayo-0.10.0-win64-binaries\mayo-conv.exe --no-progress -e out.glb model.stp
```

SHA-256 of `Mayo-0.10.0-win64-binaries.zip`:
`4CD2DF02E0D5B113873515B0E222E9944629D432FE731537204A119C3B6D74B2` — verify against this
rather than trusting the download.

A 15 MB / 1127-product STEP converts in seconds and keeps the XCAF assembly tree (node
names, designators, hierarchy) *and* the per-part colours in the glb.

Mayo's default tessellation is coarser than FreeCAD's (~154k triangles where FreeCAD
produced ~725k on the same file). For macro close-ups check facet quality on a curved part
(an SMA body is a good probe) before accepting it; meshing quality is adjustable via
`--use-settings` with an INI if needed.

## Why not FreeCAD — two real traps

FreeCAD 0.21 headless (`FreeCADCmd.exe`) *can* read the STEP and export glb, but:

1. **All colours are lost.** STEP colours live on GUI-only ViewObjects; in console mode
   they are never stored, so the exported glb has 2 materials — every part the same
   default grey. This is silent: geometry looks complete, the film would be monochrome.
2. **Nothing exports at all without manual tessellation.** `RWGltf_CafWriter` silently
   skips every node "without triangulation data" — headless FreeCAD never triangulates.
   The workaround (tessellate each `Part::Feature` and reassign its Shape) yields a
   geometry-complete but still colourless glb. It is only worth doing if you need
   FreeCAD's finer meshing for a specific part, and you then still need Mayo (or the
   GUI) for colours.

## Step 2 — the Blender MCP add-on (for interactive inspection)

The add-on lives in the Blender-lab MCP repo (`blender.org/lab/mcp-server`) under
`addon/blender_mcp_addon/`; the MCP server half is what the agent config launches
(`uv run blender-mcp`), and it connects to the add-on's TCP socket on `localhost:9876`.

Install the add-on into Blender's user extensions:

```powershell
Copy-Item <repo>\addon\blender_mcp_addon "$env:APPDATA\Blender Foundation\Blender\<ver>\extensions\user_default\blender_mcp_addon" -Recurse
```

Three traps, all hit and verified:

1. **The manifest demands Blender ≥ 5.1.** On Blender 4.2.2 LTS the add-on works — every
   API it uses (`register_cli_command`, `online_access`, app timers, extensions) exists in
   4.2 — but you must lower `blender_version_min` in the *installed copy's*
   `blender_manifest.toml` to `"4.2.0"`. Leave the source repo alone.
2. **PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM**, and Blender's TOML parser
   rejects the file with `Invalid statement (at line 1, column 1)`. Rewrite the manifest
   BOM-less: `[IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))`.
3. **The server refuses to start without online access.** Launch Blender with
   `--online-mode` (or enable it in preferences), otherwise the auto-start fails with
   "Online access must be enabled in the system preferences".

Enable it once with a `--python` script (`bpy.ops.preferences.addon_enable(module=
'bl_ext.user_default.blender_mcp_addon')` then `bpy.ops.wm.save_userpref()`), and the
server auto-starts ~1 s after every launch. Verify with
`Test-NetConnection localhost -Port 9876`.

## Step 3 — import the glb and know its quirks

```python
bpy.ops.import_scene.gltf(filepath=r"...\out.glb", loglevel=50)
```

- **Pass `loglevel=50`.** The importer logs one INFO line per node to stderr; on a
  4412-node assembly that is ~100 KB of noise that swamps any tool trying to read the
  output.
- **Scale is metres.** The STEP's millimetres arrive divided by 1000 — a 107 mm board is
  0.107 Blender units long. Decide the working scale once, at scene-build time.
- **The board may not be Z-up.** This model arrived with the board face normal on ±Y
  (glTF Y-up preserved). Check the bounding box (the thin axis is the board normal)
  before orienting anything.
- **Structure**: parts arrive as EMPTY hierarchy nodes with MESH leaves, names from the
  STEP product tree (designators like `C36`, `F2` survive). Identify parts by mesh name,
  not object name — the reference film's rule holds here too.

## Verifying the conversion is honest

- Count designator-shaped products in the STEP itself (it is plain text):
  `Select-String '=\s*PRODUCT\s*\(' model.stp` and parse the second quoted field. Compare
  against what stands in Blender. On the 125-14: 612 placed designators + named library parts.
- **A designator regex over-matches library part names.** `^[A-Z]{1,4}\d+$` happily
  matches `PTC1005` (a 1005-size package name, defined in the file but never placed in
  the assembly). A count mismatch of one part came down to exactly this. Reconcile by
  per-prefix counts, and confirm an apparently-missing part is actually *instanced*
  (`NEXT_ASSEMBLY_USAGE_OCCURRENCE` with the part as child — mind the wrapped lines)
  before treating it as dropped by the converter.
- A seating check is cheap and catches incomplete assembly inputs: for every top-level
  part, world-space bbox gap to the board's faces. Parts legitimately off the board face
  exist (heatsink sits on the SoC package; elevated connector bodies) — explain each,
  don't just threshold.
- Materials count after import: more than a handful, with varied colours, or colours were
  lost upstream.
- **STEP colours still lie** — the 125-14's vendor model is *green*; the real board is
  red. The conversion preserving colours does not make them true. Check against
  photographs of the real hardware, per the showoff-render skill's GATE 1.
