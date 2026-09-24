import re

from app.domain.models import ParsedStackTrace, StackFrame


JAVA_FRAME = re.compile(r"^\s*at\s+([\w.$<>]+)\(([^:()]+)(?::(\d+))?\)")
PYTHON_FRAME = re.compile(r'^\s*File\s+["\'](.+?)["\'],\s+line\s+(\d+),\s+in\s+(.+)$')
EXCEPTION_LINE = re.compile(r'^(?:Exception in thread "[^"]+"\s+)?([\w.$]+)(?::\s*(.*))?$')


class StackTraceParser:
    def parse(self, raw: str) -> ParsedStackTrace:
        if not raw or not raw.strip():
            raise ValueError("Stack trace cannot be empty")
        lines = raw.splitlines()
        exception_type = "UnknownException"
        message = None
        frames: list[StackFrame] = []
        for line in lines:
            java = JAVA_FRAME.match(line)
            if java:
                qualified = java.group(1)
                file_name = java.group(2)
                line_number = int(java.group(3)) if java.group(3) else None
                class_name, method_name = _split_java_symbol(qualified)
                frames.append(StackFrame(class_name, method_name, file_name, line_number, line, _is_project_frame(class_name)))
                continue
            python = PYTHON_FRAME.match(line)
            if python:
                file_name, line_number, method_name = python.groups()
                frames.append(StackFrame(None, method_name, file_name, int(line_number), line, True))
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("Caused by:"):
                continue
            match = EXCEPTION_LINE.match(stripped)
            if match and (stripped[0].isalpha() or stripped[0] == "_"):
                exception_type = match.group(1)
                message = match.group(2) or None

        return ParsedStackTrace(exception_type, message, frames, raw)


def _split_java_symbol(qualified: str) -> tuple[str, str]:
    owner, separator, method = qualified.rpartition(".")
    return (owner if separator else None, method if separator else qualified)


def _is_project_frame(class_name: str | None) -> bool:
    if not class_name:
        return True
    return not class_name.startswith(("java.", "jdk.", "sun.", "org.springframework."))
