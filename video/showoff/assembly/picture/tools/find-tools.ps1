<#
.SYNOPSIS
  Locate KiCad 10 and Blender, wherever this machine keeps them.

.DESCRIPTION
  This project moves between two machines that install things differently -- one has KiCad
  and Blender in Program Files, the other runs both unpacked under C:\tools (portable, so
  no administrator rights are needed). Hardcoding either set of paths breaks the other
  machine, so both render.ps1 and animate.ps1 ask here instead.

  Newest match wins, so a KiCad 10.0.6 or a Blender 4.6 gets picked up without an edit.
  Anything passed in explicitly is returned untouched -- the search only fills in blanks.
#>

function Find-RenderTools {
    param(
        [string] $KicadPython,
        [string] $KicadCli,
        [string] $Blender
    )

    function Find-Newest([string[]] $Globs, [string] $Leaf) {
        $hits = foreach ($g in $Globs) {
            Get-Item (Join-Path $g $Leaf) -ErrorAction SilentlyContinue
        }
        # Sort by the version in the path, so 10.0.10 beats 10.0.5 and 4.5.10 beats 4.4.3.
        # A plain string sort gets that wrong, which is the whole reason for parsing it.
        $hits | Sort-Object {
            if ($_.FullName -match '(\d+)\.(\d+)(?:\.(\d+))?') {
                $patch = 0
                if ($Matches[3]) { $patch = [int]$Matches[3] }
                [version]::new([int]$Matches[1], [int]$Matches[2], $patch)
            } else {
                [version]::new(0, 0, 0)
            }
        } -Descending | Select-Object -First 1
    }

    # KiCad 10 only: export_pcb3d.py's patches target its pcbnew, and the board file is
    # saved in the KiCad 10 format, which 9.x will not open.
    $kicadRoots = @('C:\Program Files\KiCad\1*.0', 'C:\tools\kicad-1*')
    # 4.2 is the importer's declared minimum (blender_version_min in its manifest).
    $blenderRoots = @('C:\Program Files\Blender Foundation\Blender 4.*',
                      'C:\Program Files\Blender Foundation\Blender 5.*',
                      'C:\tools\blender-4.*', 'C:\tools\blender-5.*')

    if (-not $KicadPython) { $KicadPython = (Find-Newest $kicadRoots 'bin\python.exe').FullName }
    if (-not $KicadCli) { $KicadCli = (Find-Newest $kicadRoots 'bin\kicad-cli.exe').FullName }
    if (-not $Blender) { $Blender = (Find-Newest $blenderRoots 'blender.exe').FullName }

    foreach ($pair in @(@('KiCad python', $KicadPython), @('kicad-cli', $KicadCli),
                        @('Blender', $Blender))) {
        if (-not $pair[1] -or -not (Test-Path $pair[1])) {
            throw ("could not find $($pair[0]). Searched: " +
                   ($(if ($pair[0] -eq 'Blender') { $blenderRoots } else { $kicadRoots }) -join ', ') +
                   ". Pass -KicadPython/-KicadCli/-Blender explicitly.")
        }
    }
    return @{ KicadPython = $KicadPython; KicadCli = $KicadCli; Blender = $Blender }
}
