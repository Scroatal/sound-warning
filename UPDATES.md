# Publishing Windows updates

The boys' PCs run the portable EXE. They do not need Git, Python, or a GitHub
account. Source changes are distributed as versioned GitHub Releases rather
than executing a git pull on a child's computer.

## First setup

The repository is [Scroatal/sound-warning](https://github.com/Scroatal/sound-warning).
The first published Windows release is `v0.3.1`.

1. Connect this project to the public GitHub repository above, or a fork.
2. Push the source and `.github/workflows/release.yml` to that repository.
3. Create and push the tag `v0.3.1`. The workflow verifies that the tag matches
   `sound_warning/__init__.py`, runs tests, builds Windows EXEs and publishes
   `SoundWarningPortable.exe` and `SoundWarning-Windows.zip`.
4. Install that ZIP on each PC once. Release builds embed the repository name.

For a local build before publishing:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_release.py --repository OWNER/REPOSITORY
```

Without `--repository`, the app uses `Scroatal/sound-warning`. The repository can be
changed in Settings later. Private repositories are not supported: no GitHub
credentials are bundled with the app or stored on the boys' computers.

## Each update

1. Make and test the change, then bump `__version__` (for example `0.3.2`).
2. Commit and push the source.
3. Push a matching tag, for example `v0.3.2`.

Every commit does not deploy automatically. The version tag deliberately
marks the changes ready for the boys' PCs. A manual workflow run builds an
artifact for testing without publishing it as an update.

## Update behavior

- Checks the configured public repository at startup and every 6 hours.
- Downloads only a newer stable release, limited to 150 MB, over HTTPS.
- Requires the asset's SHA-256 digest supplied by GitHub's releases API and
  verifies it again before replacement. See the [GitHub releases API](https://docs.github.com/en/rest/releases/releases).
- Automatically restarts when the control window is hidden/minimized, the
  microphone has stayed under the threshold for 10 seconds, and no warning
  or quiet-time overlay is active. A manual Install and Restart button is
  also available. This briefly pauses monitoring while the app restarts.
- Uses a helper copy of the existing portable EXE to wait for both the app
  and its PyInstaller parent process to exit. No shell script is executed.
- Keeps `SoundWarningPortable.exe.previous`, tests the new EXE, restores the
  backup if the test fails, and restarts. This is a startup self-test, not a
  guarantee against every possible runtime bug.
- Preserves the user's JSON settings in `%APPDATA%\SoundWarning`.
- Leaves the current app running if the network, download, or helper fails.
  Updates require a writable app folder, such as Documents\Sound Warning.

Staging and status files are in `.sound-warning-update-*` folders beside the
app. `result.txt` records update success/failure, never audio or volume data.
The SHA-256 check detects transfer corruption; repository access must still
be kept secure. The builds are currently unsigned Windows executables.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The tests cover meter thresholds, stale audio, multiple screens, hiding the
control window, settings migration, version checks, origin validation,
corrupted downloads and update rollback. The build additionally starts the
packaged EXE's self-test, which loads Tk and PortAudio without opening a mic.
