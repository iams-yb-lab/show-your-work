<#
.SYNOPSIS
  Board -> .pcb3d -> fabrication + assembly animation (v2) -> MP4. One command.

.DESCRIPTION
  The v2 sibling of animate.ps1. Same export stage and the same studio; a different film:
  the board is fabricated on camera out of its own layer data (copper laminate, etched,
  coated, plated, printed) and then populated by lateral component waves onto a spinning
  board, with individual introductions for the ADC, the TEC driver and the Teensy.

    export_pcb3d.py          KiCad 10 -> pcb_<variant>_v2.pcb3d
    dump_components.py       board    -> components_v2.json
    animate_assembly_v2.py   both     -> .blend + PNG frames
    tools/encode_frames.py   frames   -> H.264 MP4

  Everything it writes is *_v2, so animate.ps1's baseline outputs are never touched. That
  matters: the v1 MP4 is the comparison, and it cannot be re-rendered from this board.

.EXAMPLE
  .\animate_v2.ps1 -PlanOnly
  Prints the schedule, the sub-waves, the hero resolution and the camera/board diagnostics
  in a few seconds, without importing the board. Retime here before rendering anything.

.EXAMPLE
  .\animate_v2.ps1 -Draft
  960x540, 32 samples. Watch this before spending on finals.

.EXAMPLE
  .\animate_v2.ps1 -Frames probe -OutDir out -Samples 32
  Just the storyboard beats and the movement frames between them, into out/anim/probe_v2/.

.EXAMPLE
  .\animate_v2.ps1
  2560x1440, 128 samples.
#>
[CmdletBinding()]
param(
    [string] $Board      = "",
    [string] $Variant    = "purple",
    [string] $OutDir     = "out",
    [int]    $Width      = 2560,
    [int]    $Height     = 1440,
    [int]    $Samples    = 128,
    [string] $Frames     = "all",
    [switch] $Draft,
    [switch] $PlanOnly,
    [switch] $SkipExport,
    [switch] $NoEncode,
    [switch] $NoRender,
    [string] $KicadPython,
    [string] $KicadCli,
    [string] $Blender
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# No default board: this pipeline renders whatever KiCad file you point it at, and a default
# naming one project's board is how it stopped working the moment it was lifted out of that
# project. Pass -Board.
if (-not $Board) { throw "pass -Board <path to your .kicad_pcb>" }
if (-not (Test-Path $Board)) { throw "no board at $Board" }
. (Join-Path $PSScriptRoot "tools\find-tools.ps1")
. (Join-Path $PSScriptRoot "tools\model-swaps.ps1")
$tools = Find-RenderTools -KicadPython $KicadPython -KicadCli $KicadCli -Blender $Blender

# Mask colour and its calibrated light level, both from render.ps1's $VariantSpec -- the
# stills and both animations have to agree about what "purple" means.
$VariantSpec = @{
    black  = @{ Mask = "BLACK";  Light = 1.00 }
    red    = @{ Mask = "RED";    Light = 0.55 }
    purple = @{ Mask = "PURPLE"; Light = 0.60 }
    blue   = @{ Mask = "BLUE";   Light = 0.65 }
    green  = @{ Mask = "GREEN";  Light = 0.60 }
}
$spec = $VariantSpec[$Variant]
if (-not $spec) { throw "unknown variant '$Variant'; have: $($VariantSpec.Keys -join ', ')" }

if ($Draft) {
    $Width = 960; $Height = 540; $Samples = 32
    Write-Host "draft mode: ${Width}x${Height}, $Samples samples" -ForegroundColor Yellow
}

$SceneDir = Join-Path $OutDir "scene"
$AnimDir = if ($Frames -eq "probe") { Join-Path $OutDir "anim\probe_v2" }
           else { Join-Path $OutDir "anim\${Variant}_v2" }
foreach ($dir in @($SceneDir, $AnimDir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$pcb3d = Join-Path $SceneDir "pcb_${Variant}_v2.pcb3d"
$parts = Join-Path $SceneDir "components_v2.json"
$blend = Join-Path $SceneDir "anim_${Variant}_v2.blend"
$mp4 = Join-Path $OutDir "anim\assembly_${Variant}_v2.mp4"

Write-Host "kicad:   $($tools.KicadPython)" -ForegroundColor DarkGray
Write-Host "blender: $($tools.Blender)" -ForegroundColor DarkGray
$started = Get-Date

if (($SkipExport -or $PlanOnly) -and (Test-Path $pcb3d) -and (Test-Path $parts)) {
    Write-Host "`nreusing $pcb3d" -ForegroundColor DarkGray
}
else {
    Write-Host "`nexporting .pcb3d (mask=$($spec.Mask))" -ForegroundColor Cyan
    & $tools.KicadPython "export_pcb3d.py" $Board $pcb3d `
        --mask-color $spec.Mask --silk-color WHITE --finish ENIG --kicad-cli $tools.KicadCli `
        @(Get-ModelSwaps)
    if ($LASTEXITCODE -ne 0) { throw "pcb3d export failed" }

    Write-Host "dumping designators" -ForegroundColor Cyan
    & $tools.KicadPython "dump_components.py" $Board $parts @(Get-ModelSwaps)
    if ($LASTEXITCODE -ne 0) { throw "component dump failed" }
}

$animArgs = @("--pcb3d", $pcb3d, "--parts", $parts, "--frames", $Frames)
if ($PlanOnly) {
    $animArgs += "--plan-only"
}
else {
    $animArgs += @("--blend", $blend, "--outdir", $AnimDir,
                   "--width", $Width, "--height", $Height, "--samples", $Samples,
                   "--light-strength", $spec.Light)
    if ($NoRender) { $animArgs += "--no-render" }
}

Write-Host "`nbuilding animation v2" -ForegroundColor Cyan
& $tools.Blender --background --factory-startup --python-exit-code 1 `
    --python "animate_assembly_v2.py" -- @animArgs
if ($LASTEXITCODE -ne 0) { throw "animation build/render failed" }

if (-not $NoEncode -and -not $NoRender -and -not $PlanOnly -and $Frames -eq "all") {
    Write-Host "`nencoding MP4" -ForegroundColor Cyan
    & $tools.Blender --background --factory-startup --python-exit-code 1 `
        --python "tools\encode_frames.py" -- --frames $AnimDir --out $mp4 --fps 30
    if ($LASTEXITCODE -ne 0) { throw "encode failed" }
}

$elapsed = (Get-Date) - $started
Write-Host "`ndone in $([int]$elapsed.TotalMinutes)m $($elapsed.Seconds)s" -ForegroundColor Green
if (-not $PlanOnly) {
    Get-ChildItem $AnimDir -Filter *.png | Measure-Object |
        ForEach-Object { Write-Host "  $($_.Count) frames in $AnimDir" }
}
if (Test-Path $mp4) {
    Write-Host ("  {0}  ({1:N1} MB)" -f $mp4, ((Get-Item $mp4).Length / 1MB))
}
