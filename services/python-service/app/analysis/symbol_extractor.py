from app.analysis.utils import child_text, iter_nodes, node_end_line, node_line, node_text
from app.domain.models import Language, Symbol, SymbolType


def _symbol_id(file_path: str, node, symbol_type: SymbolType, qualified_name: str) -> str:
    return f"{file_path}:{node_line(node)}:{node_end_line(node)}:{symbol_type.value}:{qualified_name}"


class JavaSymbolExtractor:
    _class_nodes = {"class_declaration", "interface_declaration"}
    _method_nodes = {"method_declaration", "constructor_declaration"}

    def extract(self, tree, source: str, file_path: str, package_name: str | None = None) -> list[Symbol]:
        symbols: list[Symbol] = []
        if package_name is None:
            package_node = next((node for node in iter_nodes(tree.root_node) if node.type == "package_declaration"), None)
            package_name = node_text(package_node, source).removeprefix("package").strip().rstrip(";") if package_node else None

        def visit(node, parents: list[Symbol]) -> None:
            current_parents = parents
            if node.type in self._class_nodes | self._method_nodes:
                name = child_text(node, "name", source)
                if name:
                    if node.type == "interface_declaration":
                        symbol_type = SymbolType.INTERFACE
                    elif node.type in self._class_nodes:
                        symbol_type = SymbolType.CLASS
                    else:
                        symbol_type = SymbolType.METHOD
                    parent = parents[-1] if parents else None
                    qualified_name = f"{parent.qualifiedName}.{name}" if parent else name
                    if parent is None and package_name:
                        qualified_name = f"{package_name}.{name}"
                    signature = None
                    if symbol_type == SymbolType.METHOD:
                        parameters = child_text(node, "parameters", source)
                        signature = f"{name}{parameters}" if parameters else name
                    symbol = Symbol(
                        id=_symbol_id(file_path, node, symbol_type, qualified_name),
                        name=name,
                        qualifiedName=qualified_name,
                        type=symbol_type,
                        language=Language.JAVA,
                        filePath=file_path,
                        startLine=node_line(node),
                        endLine=node_end_line(node),
                        parentSymbolId=parent.id if parent else None,
                        signature=signature,
                        module=package_name,
                    )
                    symbols.append(symbol)
                    current_parents = [*parents, symbol]
            for child in node.children:
                visit(child, current_parents)

        visit(tree.root_node, [])
        return symbols


class PythonSymbolExtractor:
    _class_nodes = {"class_definition"}
    _function_nodes = {"function_definition", "async_function_definition"}

    def extract(self, tree, source: str, file_path: str, module_name: str | None = None) -> list[Symbol]:
        symbols: list[Symbol] = []
        if module_name is None:
            module_name = _python_module_name(file_path)

        def visit(node, parents: list[Symbol]) -> None:
            current_parents = parents
            if node.type in self._class_nodes | self._function_nodes:
                name = child_text(node, "name", source)
                if name:
                    parent = parents[-1] if parents else None
                    symbol_type = (
                        SymbolType.CLASS
                        if node.type in self._class_nodes
                        else (SymbolType.METHOD if parent and parent.type == SymbolType.CLASS else SymbolType.FUNCTION)
                    )
                    qualified_name = f"{parent.qualifiedName}.{name}" if parent else name
                    if parent is None and module_name:
                        qualified_name = f"{module_name}.{name}"
                    parameters = child_text(node, "parameters", source)
                    signature = f"{name}{parameters}" if parameters else name
                    symbol = Symbol(
                        id=_symbol_id(file_path, node, symbol_type, qualified_name),
                        name=name,
                        qualifiedName=qualified_name,
                        type=symbol_type,
                        language=Language.PYTHON,
                        filePath=file_path,
                        startLine=node_line(node),
                        endLine=node_end_line(node),
                        parentSymbolId=parent.id if parent else None,
                        signature=signature,
                        module=module_name,
                    )
                    symbols.append(symbol)
                    current_parents = [*parents, symbol]
            for child in node.children:
                visit(child, current_parents)

        visit(tree.root_node, [])
        return symbols


def _python_module_name(file_path: str) -> str:
    path = file_path.replace("\\", "/")
    if path.endswith(".py"):
        path = path[:-3]
    parts = [part for part in path.split("/") if part not in {".", ""}]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)
