$ErrorActionPreference = "Stop"

$Python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'python' }
Push-Location (Join-Path $PSScriptRoot '..')
try {
    & $Python scripts/build_release.py @args
    if ($LASTEXITCODE -ne 0) { throw 'Sound Warning build failed' }
} finally {
    Pop-Location
}
