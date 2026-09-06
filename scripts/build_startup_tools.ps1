$ErrorActionPreference = "Stop"

python -m PyInstaller --noconfirm --clean --onefile `
  --name InstallSoundWarningStartup `
  --distpath "dist\SoundWarning" `
  --workpath "build\InstallSoundWarningStartup" `
  --specpath "build\InstallSoundWarningStartup" `
  "scripts\startup_installer.py"

python -m PyInstaller --noconfirm --clean --onefile `
  --name RemoveSoundWarningStartup `
  --distpath "dist\SoundWarning" `
  --workpath "build\RemoveSoundWarningStartup" `
  --specpath "build\RemoveSoundWarningStartup" `
  "scripts\startup_uninstaller.py"
