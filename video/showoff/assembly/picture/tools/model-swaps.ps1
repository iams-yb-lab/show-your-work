<#
.SYNOPSIS
  Which parts render with a different 3D model than the board file names, and why.

.DESCRIPTION
  One home for the swap list, dot-sourced by both render.ps1 and animate.ps1 so the stills
  and the animation can never disagree about what the board looks like.

  A swap is a *render* decision, not a design change: export_pcb3d.py applies it to the
  board it has loaded and hands kicad-cli a temporary copy, so PCB_new.kicad_pcb is never
  written. Nothing here changes the netlist, the footprint, or the part that gets ordered.
#>

function Get-ModelSwaps {
    # U1 -- the Teensy. The board points at tools/3d-models/gen_teensy41.py's output, which
    # is dimensionally right but visually plain: pins flush with the board, a plain box for
    # the USB shell, no populated parts. This one is a real coloured CAD assembly (74 solids,
    # 2593 colour entities, a Molex 473460001 micro-USB and a Hirose DM3D-SF micro-SD as
    # named sub-parts), released by ZS6HG on the PJRC forum and carried in
    # BasicAirData/AirDataComputer. It is what blender_scene.py's Teensy material rules were
    # written against -- its mask reads linear (0, 0.497, 0), exactly the value that file
    # documents.
    #
    # It is a Teensy 3.6 standing in for the 4.1 the board carries. Same 0.1 inch outline and
    # pin lattice; the MCU, the SD-socket side and the silkscreen differ. Deliberate, and the
    # reason narration-assembly.md calls it "the controller" rather than naming it.
    #
    # The transform is derived, not eyeballed: the model's own origin is a corner, and its
    # gold pin field centres at 12 x 2.54 mm and 3.5 x 2.54 mm from it, so those exact
    # multiples put the pins on the pad lattice. z lifts the Teensy's PCB bottom -- its
    # origin is the PCB *top* face -- clear of the board by the header height.
    #
    # It has no headers of its own, so it stands on the ones tools/3d-models/
    # gen_teensy_headers.py generates: two 24-way strips and 48 posts, on the same 0.1 inch
    # lattice, imported from gen_teensy41.py so the dimensions have one home. z therefore
    # becomes 1.562 (PCB thickness) + 2.54 (standoff) = 4.102.
    $lib = '${KIPRJMOD}/kicad-libs/teensy.3dshapes'
    return @(
        '--swap-model', "U1=$lib/Teensy_3.6_assembly_ZS6HG.wrl@30.480,-8.890,4.102,0,0,0",
        '--swap-model', "U1=$lib/PinHeader_1x24x2_P2.54mm_Standoff.wrl@0,0,0,0,0,0"
    )
}

