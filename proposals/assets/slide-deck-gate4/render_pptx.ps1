# render_pptx.ps1 — render a .pptx to one PNG per slide, using PowerPoint itself.
#
# PowerPoint is the authentic renderer: it shows font substitution, autofit and
# layout drift that no library can predict, and it is the only way to see what
# the recipient will see. Run this after every PPTX rebuild and LOOK at the PNGs.
#
#   powershell -File render_pptx.ps1 -Pptx "C:\deck\exports\deck.pptx" [-Out "C:\deck\exports\pptxpng"]
#
# Needs PowerPoint installed. On a machine without it, LibreOffice is the
# fallback:  soffice --headless --convert-to pdf deck.pptx  then rasterize the PDF.

param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [string]$Out = ""
)

if (-not (Test-Path $Pptx)) { Write-Error "no such file: $Pptx"; exit 2 }
if ($Out -eq "") { $Out = Join-Path (Split-Path $Pptx) "pptxpng" }

$render = Join-Path $Out "render"
Remove-Item -Recurse -Force $render -ErrorAction SilentlyContinue
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Force $Out | Out-Null }

$pp = New-Object -ComObject PowerPoint.Application
try {
  $deck = $pp.Presentations.Open($Pptx, $true, $false, $false)   # read-only, no window
  $deck.SaveCopyAs($render, 18)                                  # 18 = ppSaveAsPNG
  $deck.Close()
} finally {
  $pp.Quit()
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
}

$pngs = Get-ChildItem -Recurse $Out -Filter *.PNG
Write-Output ("rendered " + $pngs.Count + " slides to " + $render)
Write-Output "Now LOOK at them. A passing layout check is not a reviewed slide."
