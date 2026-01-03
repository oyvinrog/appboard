from pathlib import Path

from core import parse_desktop_file, sanitize_exec


def test_sanitize_exec_removes_placeholders():
    exec_line = "app --flag %U --name %f"
    assert sanitize_exec(exec_line) == ["app", "--flag", "--name"]


def test_parse_desktop_file(tmp_path):
    desktop = tmp_path / "sample.desktop"
    desktop.write_text(
        """
[Desktop Entry]
Type=Application
Name=Sample App
Exec=sample-app --flag %U
Comment=Runs the sample app
Icon=sample-icon
""".strip(),
        encoding="utf-8",
    )
    parsed = parse_desktop_file(desktop)
    assert parsed is not None
    assert parsed["name"] == "Sample App"
    assert parsed["exec"] == ["sample-app", "--flag"]
    assert parsed["comment"] == "Runs the sample app"
    assert parsed["icon"] == "sample-icon"
    assert parsed["path"] == str(desktop)


def test_parse_desktop_file_ignores_non_apps(tmp_path):
    desktop = tmp_path / "link.desktop"
    desktop.write_text(
        """
[Desktop Entry]
Type=Link
Name=Not an app
Exec=should-not-run
""".strip(),
        encoding="utf-8",
    )
    assert parse_desktop_file(desktop) is None
