import sys

from core import determine_launch, resolve_python_for_script


def test_launch_python_script():
    method, payload = determine_launch(
        "C:/scripts/run.py", "Windows", False, True, sys.executable
    )
    assert method == "popen"
    assert payload == [sys.executable, "C:/scripts/run.py"]


def test_launch_shell_script():
    method, payload = determine_launch("/home/user/run.sh", "Linux", True, True, "python")
    assert method == "popen"
    assert payload == ["bash", "/home/user/run.sh"]


def test_launch_bat_on_windows():
    method, payload = determine_launch("C:/scripts/run.bat", "Windows", False, True, "python")
    assert method == "startfile"
    assert payload == "C:/scripts/run.bat"


def test_launch_bat_on_linux():
    method, payload = determine_launch("/home/user/run.cmd", "Linux", False, True, "python")
    assert method == "popen"
    assert payload == ["bash", "/home/user/run.cmd"]


def test_launch_powershell():
    method, payload = determine_launch("C:/scripts/run.ps1", "Windows", False, True, "python")
    assert method == "popen"
    assert payload == ["powershell", "-ExecutionPolicy", "Bypass", "-File", "C:/scripts/run.ps1"]


def test_launch_executable_on_linux():
    method, payload = determine_launch("/usr/local/bin/tool", "Linux", True, True, "python")
    assert method == "popen"
    assert payload == ["/usr/local/bin/tool"]


def test_launch_non_executable_on_linux():
    method, payload = determine_launch("/home/user/notes.txt", "Linux", False, True, "python")
    assert method == "popen"
    assert payload == ["xdg-open", "/home/user/notes.txt"]


def test_launch_on_macos():
    method, payload = determine_launch("/Applications/App.app", "Darwin", False, True, "python")
    assert method == "popen"
    assert payload == ["open", "/Applications/App.app"]


def test_resolve_python_prefers_venv(tmp_path):
    project_dir = tmp_path / "project"
    script_dir = project_dir / "scripts"
    script_dir.mkdir(parents=True)
    venv_dir = project_dir / ".venv" / "bin"
    venv_dir.mkdir(parents=True)
    python_path = venv_dir / "python"
    python_path.write_text("", encoding="utf-8")
    script_path = script_dir / "run.py"
    script_path.write_text("print('ok')", encoding="utf-8")

    resolved = resolve_python_for_script(str(script_path), "/usr/bin/python3")
    assert resolved == str(python_path)


def test_resolve_python_falls_back(tmp_path):
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    script_path = script_dir / "run.py"
    script_path.write_text("print('ok')", encoding="utf-8")

    resolved = resolve_python_for_script(str(script_path), "/usr/bin/python3")
    assert resolved == "/usr/bin/python3"
