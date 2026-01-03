# AppBoard

A lightweight dashboard for launching your favorite apps and scripts as tiles.

## Features
- Add tiles by browsing to an app or script
- On Linux, add system apps from installed `.desktop` entries
- Optional descriptions for each tile
- Handles Python scripts and common shell scripts
- Uses a nearby virtual environment for Python scripts when available
- Tiles are stored in `shortcuts.json`

## Run
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```

## Notes
- Python scripts (`.py`) run with your current Python interpreter.
- Shell scripts (`.sh`, `.bat`, `.cmd`, `.ps1`) use the standard shell for your OS.
- Everything else opens as the OS default application.
