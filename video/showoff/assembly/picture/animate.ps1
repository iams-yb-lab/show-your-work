<#
.SYNOPSIS
  Board -> .pcb3d -> assembly animation -> MP4. One command.

.DESCRIPTION
  The moving-picture sibling of render.ps1, sharing its export stage and its studio:

    export_pcb3d.py      KiCad 10 -> .pcb3d
    dump_components.py   board     -> components.json  (designators the .pcb3d lacks)
    animate_assembly.py  both      -> .blend + PNG frames
    tools/encode_frames.py  frames -> H.264 MP4

.EXAMPLE
  .\animate.ps1 -Draft
  960x540, 24 samples, ~10 min on an RTX 4080 SUPER. Watch this before spending on finals.

.EXAMPLE
  .\animate.ps1
  2560x1440, 128 samples.

.EXAMPLE
  .\animate.ps1 -Frames "305,340,415,495,600" -Samples 192
  Just the landing frames, at final quality, for judging the image rather than the motion.
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
# stills and the animation have to agree about what "purple" means.
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
    $Width = 960; $Height = 540; $Samples = 24
    Write-Host "draft mode: ${Width}x${Height}, $Samples samples" -ForegroundColor Yellow
}

$SceneDir = Join-Path $OutDir "scene"
$AnimDir = Join-Path $OutDir "anim\$Variant"
foreach ($dir in @($SceneDir, $AnimDir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$pcb3d = Join-Path $SceneDir "pcb_$Variant.pcb3d"
$parts = Join-Path $SceneDir "components.json"
$blend = Join-Path $SceneDir "anim_$Variant.blend"
$mp4 = Join-Path $OutDir "anim\assembly_$Variant.mp4"

Write-Host "kicad:   $($tools.KicadPython)" -ForegroundColor DarkGray
Write-Host "blender: $($tools.Blender)" -ForegroundColor DarkGray
$started = Get-Date

if ($SkipExport -and (Test-Path $pcb3d) -and (Test-Path $parts)) {
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

$animArgs = @(
    "--pcb3d", $pcb3d, "--parts", $parts, "--blend", $blend, "--outdir", $AnimDir,
    "--width", $Width, "--height", $Height, "--samples", $Samples,
    "--light-strength", $spec.Light, "--frames", $Frames
)
if ($NoRender) { $animArgs += "--no-render" }

Write-Host "`nbuilding + rendering animation" -ForegroundColor Cyan
& $tools.Blender --background --factory-startup --python-exit-code 1 `
    --python "animate_assembly.py" -- @animArgs
if ($LASTEXITCODE -ne 0) { throw "animation render failed" }

if (-not $NoEncode -and -not $NoRender -and $Frames -eq "all") {
    Write-Host "`nencoding MP4" -ForegroundColor Cyan
    & $tools.Blender --background --factory-startup --python-exit-code 1 `
        --python "tools\encode_frames.py" -- --frames $AnimDir --out $mp4 --fps 30
    if ($LASTEXITCODE -ne 0) { throw "encode failed" }
}

$elapsed = (Get-Date) - $started
Write-Host "`ndone in $([int]$elapsed.TotalMinutes)m $($elapsed.Seconds)s" -ForegroundColor Green
Get-ChildItem $AnimDir -Filter *.png | Measure-Object |
    ForEach-Object { Write-Host "  $($_.Count) frames in $AnimDir" }
if (Test-Path $mp4) {
    Write-Host ("  {0}  ({1:N1} MB)" -f $mp4, ((Get-Item $mp4).Length / 1MB))
}
