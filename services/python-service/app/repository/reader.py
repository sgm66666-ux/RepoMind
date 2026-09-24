from pathlib import Path

from app.domain.models import FileReadResult, Language, RequestedRange


class CodeReader:
    """Read only source files below the analyzed repository root."""

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()

    def read(self, file_path: str, start_line: int | None = None, end_line: int | None = None) -> FileReadResult:
        if not file_path or "\x00" in file_path:
            raise ValueError("filePath must be a non-empty relative source path")
        if Path(file_path).is_absolute():
            raise ValueError("filePath must be relative to the analyzed repository")
        candidate = (self.root / Path(file_path)).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("filePath must stay within the analyzed repository") from exc
        if candidate.suffix.lower() not in {".java", ".py"}:
            raise ValueError("Only .java and .py source files can be read")
        if not candidate.is_file():
            raise FileNotFoundError(f"Source file does not exist: {file_path}")
        try:
            content = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Source file is not valid UTF-8: {file_path}") from exc

        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            if start_line not in (None, 1) or end_line not in (None, 1):
                raise ValueError("Line range is outside an empty file")
            requested = RequestedRange(1, 0)
            selected = ""
        else:
            start = 1 if start_line is None else start_line
            end = total_lines if end_line is None else end_line
            if start < 1 or end < start or end > total_lines:
                raise ValueError(f"Line range must be within 1..{total_lines}")
            requested = RequestedRange(start, end)
            selected = "\n".join(lines[start - 1 : end])

        language = Language.JAVA if candidate.suffix.lower() == ".java" else Language.PYTHON
        relative = candidate.relative_to(self.root).as_posix()
        return FileReadResult(relative, language, requested, selected)
