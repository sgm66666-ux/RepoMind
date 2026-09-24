from pathlib import Path

import pytest

from app.repository.scanner import RepositoryScanner


def test_scanner_reads_supported_files_and_ignores_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "target").mkdir()
    (tmp_path / "src" / "empty.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "Main.java").write_text("class Main {}", encoding="utf-8")
    (tmp_path / ".git" / "ignored.py").write_text("def ignored(): pass", encoding="utf-8")
    (tmp_path / "target" / "ignored.java").write_text("class Ignored {}", encoding="utf-8")

    result = RepositoryScanner().scan(tmp_path)

    assert [item.filePath for item in result.files] == ["src/empty.py", "src/Main.java"]
    assert result.files[0].content == ""
    assert result.issues == []


def test_scanner_reports_bad_encoding_and_missing_paths(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.py"
    bad_file.write_bytes(b"\xff\xfe")
    result = RepositoryScanner().scan(tmp_path)
    assert len(result.issues) == 1
    assert result.issues[0].filePath == "bad.py"

    with pytest.raises(FileNotFoundError):
        RepositoryScanner().scan(tmp_path / "missing")
