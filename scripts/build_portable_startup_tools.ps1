$ErrorActionPreference = "Stop"

python -m PyInstaller --noconfirm --clean --onefile `
  --name InstallSoundWarningStartup `
  --distpath "dist" `
  --workpath "build\InstallSoundWarningStartupPortable" `
  --specpath "build\InstallSoundWarningStartupPortable" `
  "scripts\startup_installer.py"

python -m PyInstaller --noconfirm --clean --onefile `
  --name RemoveSoundWarningStartup `
  --distpath "dist" `
  --workpath "build\RemoveSoundWarningStartupPortable" `
  --specpath "build\RemoveSoundWarningStartupPortable" `
  "scripts\startup_uninstaller.py"
