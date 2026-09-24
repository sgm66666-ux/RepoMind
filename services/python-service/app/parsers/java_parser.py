import tree_sitter_java
from tree_sitter import Language as TreeSitterLanguage
from tree_sitter import Parser, Tree

from app.domain.models import Language
from app.parsers.base import BaseParser


class JavaParser(BaseParser):
    language = Language.JAVA

    def __init__(self) -> None:
        self._parser = Parser(TreeSitterLanguage(tree_sitter_java.language()))

    def parse(self, sourceCode: str) -> Tree:
        return self._parser.parse(sourceCode.encode("utf-8"))
