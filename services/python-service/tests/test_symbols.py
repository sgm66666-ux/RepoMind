from app.parsers.java_parser import JavaParser
from app.parsers.python_parser import PythonParser
from app.analysis.symbol_extractor import JavaSymbolExtractor, PythonSymbolExtractor
from app.domain.models import SymbolType


def test_java_symbol_extraction_sets_parent_and_source_lines() -> None:
    source = "class OrderService {\n  void createOrder() {}\n}\n"
    symbols = JavaSymbolExtractor().extract(JavaParser().parse(source), source, "OrderService.java")
    names = {(symbol.qualifiedName, symbol.type) for symbol in symbols}
    assert ("OrderService", SymbolType.CLASS) in names
    method = next(symbol for symbol in symbols if symbol.name == "createOrder")
    assert method.qualifiedName == "OrderService.createOrder"
    assert method.parentSymbolId == next(symbol for symbol in symbols if symbol.name == "OrderService").id
    assert method.startLine == 2 and method.endLine == 2


def test_python_symbol_extraction_distinguishes_function_and_method() -> None:
    source = "def top():\n    pass\n\nclass OrderService:\n    def create_order(self):\n        pass\n"
    symbols = PythonSymbolExtractor().extract(PythonParser().parse(source), source, "service.py")
    top = next(symbol for symbol in symbols if symbol.name == "top")
    method = next(symbol for symbol in symbols if symbol.name == "create_order")
    assert top.type == SymbolType.FUNCTION
    assert method.type == SymbolType.METHOD
    assert method.qualifiedName == "service.OrderService.create_order"
    assert method.startLine == 5 and method.endLine == 6
