import configparser
import json
import os
import shlex
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


def sanitize_exec(exec_line):
    parts = shlex.split(exec_line)
    return [part for part in parts if not part.startswith("%")]


def parse_desktop_file(path):
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return None

    if "Desktop Entry" not in config:
        return None

    entry = config["Desktop Entry"]
    if entry.get("Type") != "Application":
        return None

    name = entry.get("Name")
    exec_line = entry.get("Exec")
    if not name or not exec_line:
        return None

    return {
        "name": name,
        "exec": sanitize_exec(exec_line),
        "comment": entry.get("Comment", ""),
        "icon": entry.get("Icon", ""),
        "path": str(path),
    }


def list_desktop_apps():
    paths = [
        Path("/usr/share/applications"),
        Path.home() / ".local" / "share" / "applications",
    ]
    apps = []
    for base in paths:
        if not base.exists():
            continue
        for desktop_file in base.glob("*.desktop"):
            parsed = parse_desktop_file(desktop_file)
            if parsed:
                apps.append(parsed)
    apps.sort(key=lambda item: item["name"].lower())
    return apps


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
