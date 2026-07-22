# Build hogwarts-agent.exe on native Windows (PyInstaller).
# Usage (from repo root or this folder):
#   pwsh -File agent/windows/build-windows.ps1
#   pwsh -File agent/windows/build-windows.ps1 -OutDir D:\artifacts
param(
    [string]$OutDir = "",
    [string]$Name = "hogwarts-agent"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$AgentPy = Join-Path $Root "agent\agent.py"
if (-not (Test-Path $AgentPy)) {
    throw "agent.py not found at $AgentPy"
}
if (-not $OutDir) {
    $OutDir = Join-Path $Root "dist\agent-windows"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "=== Hogwarts Windows agent build ==="
Write-Host "Root: $Root"
Write-Host "Out:  $OutDir"

# Prefer full python.exe over Windows `py` launcher (py often has no SDK / -3 fails).
function Test-PythonExe([string]$cmd) {
    try {
        $out = & $cmd -c "import sys; print(sys.version)" 2>$null
        return ($LASTEXITCODE -eq 0 -and $out)
    } catch { return $false }
}

$py = $null
$usePyLauncherArgs = $false
foreach ($c in @("python", "python3", "py")) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
    if ($c -eq "py") {
        # Only use py if `py -3` works
        try {
            $v = & py -3 -c "import sys; print(sys.version)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) {
                $py = "py"
                $usePyLauncherArgs = $true
                break
            }
        } catch {}
        continue
    }
    if (Test-PythonExe $c) {
        $py = $c
        break
    }
}
if (-not $py) { throw "Python 3.10+ not on PATH (python/python3; py -3 also ok)" }
Write-Host "Using interpreter: $py$(if ($usePyLauncherArgs) { ' -3' })"

function Invoke-Py([string[]]$PyArgs) {
    if ($usePyLauncherArgs) {
        & $py -3 @PyArgs
    } else {
        & $py @PyArgs
    }
}

Invoke-Py @("-m", "pip", "install", "-q", "pyinstaller>=6.0")
if ($LASTEXITCODE -ne 0) {
    Invoke-Py @("-m", "pip", "install", "-q", "pyinstaller>=6.0")
}

$work = Join-Path $OutDir "build"
$spec = $OutDir
$piArgs = @(
    "-m", "PyInstaller",
    "--onefile", "--clean", "--noconfirm",
    "--name", $Name,
    "--distpath", $OutDir,
    "--workpath", $work,
    "--specpath", $spec,
    $AgentPy
)
Invoke-Py $piArgs
if ($LASTEXITCODE -ne 0) {
    Invoke-Py $piArgs
}

$exe = Join-Path $OutDir "$Name.exe"
if (-not (Test-Path $exe)) { throw "Build finished but $exe missing" }
Get-Item $exe | Format-List FullName, Length, LastWriteTime

Write-Host ""
Write-Host "Keepstream 60fps: install ffmpeg and put it on PATH (gdigrab)."
Write-Host "  winget install Gyan.FFmpeg   # or chocolatey ffmpeg"
Write-Host "Run:  $exe loop -c agent.json"
