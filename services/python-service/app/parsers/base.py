from abc import ABC, abstractmethod

from tree_sitter import Tree

from app.domain.models import Language


class BaseParser(ABC):
    language: Language

    @abstractmethod
    def parse(self, sourceCode: str) -> Tree:
        """Parse source code and return the real tree-sitter tree."""
