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

$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        $py = $c
        break
    }
}
if (-not $py) { throw "Python 3.10+ not on PATH (py/python)" }

& $py -3 -m pip install -q "pyinstaller>=6.0"
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install -q "pyinstaller>=6.0"
}

$work = Join-Path $OutDir "build"
$spec = $OutDir
& $py -3 -m PyInstaller `
    --onefile --clean --noconfirm `
    --name $Name `
    --distpath $OutDir `
    --workpath $work `
    --specpath $spec `
    $AgentPy
if ($LASTEXITCODE -ne 0) {
    & $py -m PyInstaller `
        --onefile --clean --noconfirm `
        --name $Name `
        --distpath $OutDir `
        --workpath $work `
        --specpath $spec `
        $AgentPy
}

$exe = Join-Path $OutDir "$Name.exe"
if (-not (Test-Path $exe)) { throw "Build finished but $exe missing" }
Get-Item $exe | Format-List FullName, Length, LastWriteTime

Write-Host ""
Write-Host "Keepstream 60fps: install ffmpeg and put it on PATH (gdigrab)."
Write-Host "  winget install Gyan.FFmpeg   # or chocolatey ffmpeg"
Write-Host "Run:  $exe loop -c agent.json"
