from core import load_tiles_file, save_tiles_file


def test_load_empty_when_missing(tmp_path):
    path = tmp_path / "missing.json"
    assert load_tiles_file(path) == []


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "shortcuts.json"
    tiles = [
        {
            "name": "Run Script",
            "path": "C:/scripts/run.py",
            "description": "Nightly task",
        }
    ]
    save_tiles_file(path, tiles)
    assert load_tiles_file(path) == tiles


def test_load_invalid_json_returns_empty(tmp_path):
    path = tmp_path / "shortcuts.json"
    path.write_text("{bad json}", encoding="utf-8")
    assert load_tiles_file(path) == []
