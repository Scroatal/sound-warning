# Sound Warning

## Live meter and automatic updates (0.3.0)

Use `dist\SoundWarning-Windows.zip` for the current release. Extract it to a
permanent writable folder, open `SoundWarningPortable.exe`, and enable startup
with `InstallSoundWarningStartup.exe` if required.

The always-visible meter runs across the top of each screen. Green means inside
voice, amber means approaching the warning threshold, and red means too loud.
It uses the exact smoothed RMS level used by the detector. The strip is
click-through and stays visible when the settings window is hidden. Monitoring
and Updates controls are in separate tabs; Save Settings applies both tabs.

The portable app can download and install new releases from a configured public
GitHub repository. It checks at startup and every 6 hours. Automatic installation
waits until the app is hidden/minimized and quiet, then restarts it. Existing
settings are preserved. No Git or Python installation is needed on the boys' PCs.
See [UPDATES.md](UPDATES.md) for repository setup, publishing and rollback details.

No repository is assumed for a local build: enter `owner/repository` in Updates.
Builds produced by the GitHub release workflow include the repository address.

Build all three EXEs and the ZIP with:

```powershell
.\.venv\Scripts\python.exe scripts/build_release.py --repository OWNER/REPOSITORY
```

The latest portable app opens a normal Windows control window with editable sensitivity,
warning count, quiet-time duration, and a Test Warning button. A warning flashes a red
border around all four edges of the primary screen for four seconds, with the message
"Boys, you're being too loud". The desktop remains visible inside the border.
Repeated warnings still trigger the timed quiet-time overlay.

Close the control window to keep monitoring in the tray; use Quit to stop it.
The startup installer enables background launch at sign-in. Keep the extracted app in
its permanent folder before running the installer. No Python installation is required.
The overlay is intended for the Windows desktop and windowed applications; exclusive
fullscreen games may appear above normal Windows overlays.

Sound Warning is a Windows desktop behaviour-training app for kids. It monitors microphone loudness only and shows a border warning when loud sound continues for the configured duration.

Privacy rules:

- No audio files are recorded.
- No audio is saved.
- No audio is uploaded.
- No speech recognition or transcription is used.
- Only live RMS loudness values are calculated in memory.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m sound_warning
```

Python 3.11 or newer is recommended. The app was written to keep dependencies simple: `sounddevice`, `numpy`, and the Python standard library UI toolkit `tkinter`.

## Settings

On first run the app creates:

```text
%APPDATA%\SoundWarning\settings.json
```

Default settings:

```json
{
  "yell_duration_seconds": 1.0,
  "loudness_threshold": 0.08,
  "smoothing_factor": 0.4,
  "warning_limit": 3,
  "lock_seconds": 15,
  "sample_rate": 16000,
  "chunk_milliseconds": 100,
  "show_meter": true,
  "auto_update": true,
  "update_repository": ""
}
```

To change the sensitivity, edit `loudness_threshold`. Lower values trigger more easily; higher values require louder sound.

## Build Windows EXE

```powershell
.\scripts\build.ps1
```

The current build produces the portable app and both startup helpers in `dist`,
plus `dist\SoundWarning-Windows.zip`. The older `dist\SoundWarning` folder is a
legacy build and is not refreshed by this command. Use the portable build:

```text
dist\SoundWarningPortable.exe
```

Use this if you want to copy only a few standalone files to another computer. For the portable version, copy these files together:

```text
dist\SoundWarningPortable.exe
dist\InstallSoundWarningStartup.exe
dist\RemoveSoundWarningStartup.exe
```

## Start With Windows

After building the startup helper executables, the app folder contains:

```text
InstallSoundWarningStartup.exe
RemoveSoundWarningStartup.exe
```

On the target computer, run:

```text
InstallSoundWarningStartup.exe
```

This creates a startup entry for the current Windows user. Sound Warning will start when that user signs in.

To remove startup later, run:

```text
RemoveSoundWarningStartup.exe
```

PowerShell scripts are also available for development use:

```powershell
.\scripts\install_startup.ps1
```

```powershell
.\scripts\uninstall_startup.ps1
```

## Notes

Audio processing is local-only. The optional updater downloads software releases
from GitHub; it does not send audio or loudness readings. There is no speech-to-text,
account login, or remote audio monitoring.
