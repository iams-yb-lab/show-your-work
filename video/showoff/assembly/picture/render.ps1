<#
.SYNOPSIS
  Board -> .pcb3d -> studio-lit Blender scene -> presentation stills. One command.

.DESCRIPTION
  Two stages, both scripted so the whole thing is reproducible from the .kicad_pcb:

    export_pcb3d.py   KiCad 10 -> .pcb3d   (run by KiCad's bundled python)
    blender_scene.py  .pcb3d -> .blend + PNGs

  Colour variants are produced by overriding the stackup at export time, so the board
  file is never modified -- PCB_new.kicad_pcb keeps whatever mask colour it has.

.EXAMPLE
  .\render.ps1 -Draft
  Fast 960x540 preview of every shot and variant. Use this while adjusting.

.EXAMPLE
  .\render.ps1
  Full 3840x2160 finals.

.EXAMPLE
  .\render.ps1 -Variants purple -Shots showcase -Samples 512
  One high-sample showcase. Pass -OutDir out\scratch when testing -- a draft run at the
  default overwrites the finished still of the same name.
#>
[CmdletBinding()]
param(
    [string]   $Board      = "..\..\..\..\PCB\PCB_new.kicad_pcb",
    [string]   $OutDir     = "out",
    [string[]] $Variants   = @("red", "purple"),
    [string]   $Shots      = "slide,cinematic,showcase,demo",
    [int]      $Width      = 3840,
    [int]      $Height     = 2160,
    [int]      $Samples    = 256,
    [switch]   $Draft,
    [switch]   $SkipExport,
    [switch]   $AlphaToo,
    [string]   $KicadPython,
    [string]   $KicadCli,
    [string]   $Blender
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# The two machines install KiCad and Blender in different places, so the paths are found
# rather than hardcoded. Pass -KicadPython/-KicadCli/-Blender to override.
. (Join-Path $PSScriptRoot "tools\find-tools.ps1")
. (Join-Path $PSScriptRoot "tools\model-swaps.ps1")
$tools = Find-RenderTools -KicadPython $KicadPython -KicadCli $KicadCli -Blender $Blender
$KicadPython = $tools.KicadPython
$KicadCli = $tools.KicadCli
$Blender = $tools.Blender

# Invoked as `powershell -File render.ps1 -Variants red,purple` the comma-separated list
# arrives as one literal string rather than an array, so split it back apart. Accepts both
# `-Variants red,purple` and `-Variants red purple`.
$Variants = $Variants | ForEach-Object { $_ -split "," } | Where-Object { $_ -ne "" }

# Soldermask / silkscreen / copper finish per variant. Mask and silk accept KiCad colour
# names (BLACK BLUE PURPLE RED WHITE YELLOW GREEN) or #RRGGBB.
#
# Light carries the exposure for that mask, because albedo and light level have to move
# together: the same rig that exposes a black board correctly is about a stop hot on red
# or purple and washes the traces out. These were set by measuring mean luma into the
# 0.16-0.34 band (tools/measure_exposure.py), not by eye.
$VariantSpec = @{
    black  = @{ Mask = "BLACK";  Silk = "WHITE"; Finish = "ENIG"; Light = 1.00 }
    red    = @{ Mask = "RED";    Silk = "WHITE"; Finish = "ENIG"; Light = 0.55 }
    purple = @{ Mask = "PURPLE"; Silk = "WHITE"; Finish = "ENIG"; Light = 0.60 }
    blue   = @{ Mask = "BLUE";   Silk = "WHITE"; Finish = "ENIG"; Light = 0.65 }
    green  = @{ Mask = "GREEN";  Silk = "WHITE"; Finish = "ENIG"; Light = 0.60 }
}

if ($Draft) {
    $Width = 960; $Height = 540; $Samples = 64
    Write-Host "draft mode: ${Width}x${Height}, $Samples samples" -ForegroundColor Yellow
}

if (-not (Test-Path $Board)) { throw "no board at $Board" }
Write-Host "kicad:   $KicadPython" -ForegroundColor DarkGray
Write-Host "blender: $Blender" -ForegroundColor DarkGray

# Three kinds of thing land here and they have very different lifetimes, so they get their own
# directories rather than sharing one: the stills are the output, the scene files are heavy
# regenerable intermediates (~66 MB per variant once Blender's .blend1 backup appears), and
# the comparison sheets are working material. Flat, this directory reached 70 files.
$StillsDir = Join-Path $OutDir "stills"
$SceneDir = Join-Path $OutDir "scene"
foreach ($dir in @($OutDir, $StillsDir, $SceneDir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$started = Get-Date

foreach ($variant in $Variants) {
    $spec = $VariantSpec[$variant]
    if (-not $spec) { throw "unknown variant '$variant'; have: $($VariantSpec.Keys -join ', ')" }

    $pcb3d = Join-Path $SceneDir "pcb_$variant.pcb3d"
    $blend = Join-Path $SceneDir "pcb_$variant.blend"

    if ($SkipExport -and (Test-Path $pcb3d)) {
        Write-Host "`n[$variant] reusing $pcb3d" -ForegroundColor DarkGray
    }
    else {
        Write-Host "`n[$variant] exporting .pcb3d (mask=$($spec.Mask) silk=$($spec.Silk) finish=$($spec.Finish))" -ForegroundColor Cyan
        & $KicadPython "export_pcb3d.py" $Board $pcb3d `
            --mask-color $spec.Mask --silk-color $spec.Silk --finish $spec.Finish `
            --kicad-cli $KicadCli @(Get-ModelSwaps)
        if ($LASTEXITCODE -ne 0) { throw "pcb3d export failed for $variant" }
    }

    Write-Host "[$variant] rendering $Shots at ${Width}x${Height}, $Samples samples, light $($spec.Light)" -ForegroundColor Cyan
    & $Blender --background --factory-startup --python-exit-code 1 --python "blender_scene.py" -- `
        --pcb3d $pcb3d --blend $blend --outdir $StillsDir --prefix $variant `
        --shot $Shots --width $Width --height $Height --samples $Samples `
        --light-strength $spec.Light
    # No --backdrop here on purpose: each shot carries its own (slide is transparent, demo
    # is a bright sweep, the rest are dark). Passing one overrides all of them.
    if ($LASTEXITCODE -ne 0) { throw "render failed for $variant" }

    if ($AlphaToo) {
        # Transparent background: drop these straight onto a slide of any colour.
        Write-Host "[$variant] rendering alpha cut-outs" -ForegroundColor Cyan
        & $Blender --background --factory-startup --python-exit-code 1 --python "blender_scene.py" -- `
            --pcb3d $pcb3d --outdir $StillsDir --prefix "${variant}_alpha" `
            --shot $Shots --width $Width --height $Height --samples $Samples `
            --backdrop none --light-strength $spec.Light
        if ($LASTEXITCODE -ne 0) { throw "alpha render failed for $variant" }
    }
}

$elapsed = (Get-Date) - $started
Write-Host "`ndone in $([int]$elapsed.TotalMinutes)m $($elapsed.Seconds)s" -ForegroundColor Green
Get-ChildItem $StillsDir -Filter *.png | Sort-Object Name |
    Format-Table Name, @{N = "MB"; E = { [math]::Round($_.Length / 1MB, 2) } } -AutoSize
