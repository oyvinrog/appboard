import json
import os
from pathlib import Path


def load_tiles_file(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_tiles_file(path, tiles):
    path.write_text(json.dumps(tiles, indent=2), encoding="utf-8")


def _venv_python_for_dir(base_dir):
    candidates = [".venv", "venv", ".env", "env"]
    for name in candidates:
        venv_dir = base_dir / name
        if os.name == "nt":
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            python_path = venv_dir / "bin" / "python"
        if python_path.exists():
            return str(python_path)
    return None


def resolve_python_for_script(path, fallback_python):
    script_path = Path(path)
    for base in [script_path.parent, script_path.parent.parent]:
        python_path = _venv_python_for_dir(base)
        if python_path:
            return python_path
    return fallback_python


def determine_launch(path, platform_name, is_executable, is_file, python_executable):
    lower = path.lower()
    if lower.endswith(".py"):
        python_path = resolve_python_for_script(path, python_executable)
        return "popen", [python_path, path]
    if lower.endswith(".sh"):
        return "popen", ["bash", path]
    if lower.endswith(".bat") or lower.endswith(".cmd"):
        if platform_name == "Windows":
            return "startfile", path
        return "popen", ["bash", path]
    if lower.endswith(".ps1"):
        return "popen", ["powershell", "-ExecutionPolicy", "Bypass", "-File", path]

    if platform_name == "Windows":
        return "startfile", path
    if platform_name == "Darwin":
        return "popen", ["open", path]
    if is_executable and is_file:
        return "popen", [path]
    return "popen", ["xdg-open", path]
