$ErrorActionPreference = "Stop"

$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "Sound Warning.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item -LiteralPath $ShortcutPath
    Write-Host "Removed startup shortcut:"
    Write-Host $ShortcutPath
} else {
    Write-Host "No Sound Warning startup shortcut was found."
}
