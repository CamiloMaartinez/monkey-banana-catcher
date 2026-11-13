# Builds a Windows version of the game that runs without installing Python.
# Run it from the monkey-gestures folder, with the virtual environment active:
#     ..\.venv\Scripts\Activate.ps1
#     .\build_exe.ps1
# Result: dist\MonkeyBananaCatcher\MonkeyBananaCatcher.exe  (zip that whole folder to share it).
# The folder is big (about 1 GB) because PyTorch and MediaPipe are inside.
# A console window opens too: it shows errors and the play report at the end.

$ErrorActionPreference = "Stop"
pip install pyinstaller

pyinstaller --noconfirm --clean `
    --name MonkeyBananaCatcher `
    --collect-all mediapipe `
    --hidden-import train `
    game.py

# Files the game reads and writes live next to the .exe (see gestures/config.py ROOT)
$dist = "dist\MonkeyBananaCatcher"
Copy-Item -Recurse -Force models "$dist\models"
New-Item -ItemType Directory -Force "$dist\data\raw" | Out-Null
Copy-Item -Recurse -Force data\raw\* "$dist\data\raw"   # team data, needed by CALIBRATE
Write-Host "Done: $dist\MonkeyBananaCatcher.exe"
