from app.parsers.java_parser import JavaParser
from app.parsers.python_parser import PythonParser


def test_java_parser_returns_real_tree_and_recovers_from_syntax_error() -> None:
    tree = JavaParser().parse("class Demo { void run() {} }")
    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error

    broken = JavaParser().parse("class Demo { void run( {")
    assert broken.root_node.type == "program"
    assert broken.root_node.has_error


def test_python_parser_handles_empty_and_valid_source() -> None:
    assert PythonParser().parse("").root_node.type == "module"
    tree = PythonParser().parse("def run():\n    return 1\n")
    assert tree.root_node.type == "module"
    assert not tree.root_node.has_error
