from dataclasses import dataclass
from pathlib import Path

from app.domain.models import Language, SourceFile


SUPPORTED_SUFFIXES = {".java": Language.JAVA, ".py": Language.PYTHON}
IGNORED_DIRECTORIES = {
    ".git",
    "target",
    "build",
    "dist",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
}


@dataclass(frozen=True)
class ScanIssue:
    filePath: str
    reason: str


@dataclass(frozen=True)
class ScanResult:
    files: list[SourceFile]
    issues: list[ScanIssue]


class RepositoryScanner:
    """Recursively collect UTF-8 Java and Python source files."""

    def scan(self, repository_path: str | Path) -> ScanResult:
        root = Path(repository_path)
        if not root.exists():
            raise FileNotFoundError(f"Repository does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {root}")

        files: list[SourceFile] = []
        issues: list[ScanIssue] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
                continue

            relative_path = path.relative_to(root).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                issues.append(ScanIssue(relative_path, f"encoding error: {exc}"))
                continue
            except OSError as exc:
                issues.append(ScanIssue(relative_path, f"read error: {exc}"))
                continue

            files.append(SourceFile(relative_path, SUPPORTED_SUFFIXES[path.suffix.lower()], content))
        return ScanResult(files, issues)
