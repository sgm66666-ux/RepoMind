import tree_sitter_python
from tree_sitter import Language as TreeSitterLanguage
from tree_sitter import Parser, Tree

from app.domain.models import Language
from app.parsers.base import BaseParser


class PythonParser(BaseParser):
    language = Language.PYTHON

    def __init__(self) -> None:
        self._parser = Parser(TreeSitterLanguage(tree_sitter_python.language()))

    def parse(self, sourceCode: str) -> Tree:
        return self._parser.parse(sourceCode.encode("utf-8"))
