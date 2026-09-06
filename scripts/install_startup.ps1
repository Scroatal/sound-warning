$ErrorActionPreference = "Stop"

$AppDir = Resolve-Path (Join-Path $PSScriptRoot "..\dist\SoundWarning")
$ExePath = Join-Path $AppDir "SoundWarning.exe"

if (-not (Test-Path $ExePath)) {
    throw "Could not find SoundWarning.exe at $ExePath. Run scripts\build.ps1 first."
}

$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "Sound Warning.lnk"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $AppDir
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Start Sound Warning when this Windows user signs in"
$Shortcut.Save()

Write-Host "Created startup shortcut:"
Write-Host $ShortcutPath
Write-Host ""
Write-Host "Sound Warning will start automatically when this Windows user signs in."
