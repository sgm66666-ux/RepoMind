from collections import defaultdict

from app.analysis.utils import child_text, iter_nodes, node_line, node_text
from app.domain.models import Relation, RelationType, SourceFile, Symbol, SymbolType
from app.analysis.resolver import ReceiverBinding, SymbolResolver


def _relation_id(source_id: str | None, relation_type: RelationType, target_name: str, file_path: str, line: int) -> str:
    return f"{file_path}:{line}:{relation_type.value}:{source_id or '<file>'}:{target_name}"


class RelationExtractor:
    def extract(
        self,
        source_file: SourceFile,
        tree,
        symbols: list[Symbol],
        resolver: SymbolResolver,
    ) -> list[Relation]:
        result: list[Relation] = []
        imports: set[str] = set()
        symbols_by_file: dict[str, list[Symbol]] = defaultdict(list)
        for symbol in symbols:
            symbols_by_file[symbol.filePath].append(symbol)

        def enclosing_symbol(node) -> Symbol | None:
            line = node_line(node)
            candidates = [
                symbol
                for symbol in symbols_by_file[source_file.filePath]
                if symbol.startLine <= line <= symbol.endLine
            ]
            return min(candidates, key=lambda item: (item.endLine - item.startLine, -item.startLine), default=None)

        def add(source_symbol: Symbol | None, target_name: str, relation_type: RelationType, node, evidence: str,
                target: Symbol | None = None, resolution_method: str | None = None) -> None:
            result.append(
                Relation(
                    id=_relation_id(source_symbol.id if source_symbol else None, relation_type, target_name, source_file.filePath, node_line(node)),
                    sourceSymbolId=source_symbol.id if source_symbol else None,
                    targetSymbolId=target.id if target else None,
                    targetName=target_name,
                    type=relation_type,
                    filePath=source_file.filePath,
                    line=node_line(node),
                    resolved=target is not None,
                    evidence=evidence,
                    resolutionMethod=resolution_method,
                )
            )

        def declarations(node) -> dict[str, str]:
            environment: dict[str, str] = {}
            for candidate in iter_nodes(node):
                if candidate.type not in {"field_declaration", "local_variable_declaration", "typed_parameter"}:
                    continue
                type_node = candidate.child_by_field_name("type")
                type_name = node_text(type_node, source_file.content).split("<", 1)[0] if type_node else None
                if not type_name:
                    continue
                for child in iter_nodes(candidate):
                    if child.type in {"variable_declarator", "identifier"}:
                        name_node = child.child_by_field_name("name") if child.type == "variable_declarator" else child
                        if name_node is not None:
                            environment.setdefault(node_text(name_node, source_file.content), type_name)
            return environment

        environment = declarations(tree.root_node)

        # Bind only direct constructor assignments. An alias is accepted only when
        # its import names one unique indexed class; unrelated same-name classes
        # must never be selected by a global name guess.
        python_bindings: dict[str, dict[str, tuple[int, ReceiverBinding | None]]] = defaultdict(dict)
        class_bindings: dict[str, dict[str, tuple[int, ReceiverBinding | None]]] = defaultdict(dict)
        invalid_bindings: set[tuple[str, str]] = set()
        import_aliases: dict[str, str] = {}
        if source_file.language.value == "PYTHON":
            for node in iter_nodes(tree.root_node):
                if node.type != "import_from_statement":
                    continue
                module_node = node.child_by_field_name("module_name")
                module = node_text(module_node, source_file.content) if module_node else ""
                for child in node.children:
                    if child.type not in {"dotted_name", "aliased_import"} or child == module_node:
                        continue
                    name_node = child.child_by_field_name("name") if child.type == "aliased_import" else child
                    alias_node = child.child_by_field_name("alias") if child.type == "aliased_import" else None
                    name = node_text(name_node, source_file.content)
                    alias = node_text(alias_node, source_file.content) if alias_node else name
                    if name and alias:
                        import_aliases[alias] = f"{module}.{name}"

            def constructor_binding(call_node) -> ReceiverBinding | None:
                if call_node is None or call_node.type != "call":
                    return None
                function = call_node.child_by_field_name("function")
                if function is None or function.type != "identifier":
                    return None
                name = node_text(function, source_file.content)
                candidates = [item for item in resolver.by_name.get(name, [])
                              if item.type == SymbolType.CLASS and item.filePath == source_file.filePath]
                method = "LOCAL_CONSTRUCTOR_ASSIGNMENT"
                if name in import_aliases:
                    imported = import_aliases[name]
                    candidates = [item for item in symbols if item.type == SymbolType.CLASS and
                                  item.name == imported.rsplit(".", 1)[-1] and
                                  (item.module == imported.rsplit(".", 1)[0] or
                                   (item.module or "").endswith("." + imported.rsplit(".", 1)[0]))]
                    method = "IMPORTED_CONSTRUCTOR_ASSIGNMENT"
                if len(candidates) != 1:
                    return None
                return ReceiverBinding(candidates[0].id, method)

            for node in iter_nodes(tree.root_node):
                if node.type != "assignment":
                    continue
                method_symbol = enclosing_symbol(node)
                if not method_symbol or method_symbol.type not in {SymbolType.METHOD, SymbolType.FUNCTION}:
                    continue
                # Only a direct statement in the function body is stable across
                # branches; do not infer types from conditional assignments.
                statement = node.parent
                block = statement.parent if statement else None
                definition = block.parent if block else None
                if not (statement and statement.type == "expression_statement" and block and
                        block.type == "block" and definition and definition.type in
                        {"function_definition", "async_function_definition"}):
                    continue
                left = node.child_by_field_name("left")
                right = node.child_by_field_name("right")
                if not left:
                    continue
                binding = constructor_binding(right)
                receiver = node_text(left, source_file.content)
                if left.type == "attribute" and receiver.startswith("self.") and method_symbol.name == "__init__":
                    if method_symbol.parentSymbolId:
                        owner = method_symbol.parentSymbolId
                        previous = class_bindings[owner].get(receiver)
                        if previous and previous[1] != binding:
                            invalid_bindings.add((owner, receiver))
                        class_bindings[owner][receiver] = (node_line(node), binding)
                elif left.type == "identifier":
                    owner = method_symbol.id
                    previous = python_bindings[owner].get(receiver)
                    if previous and previous[1] != binding:
                        invalid_bindings.add((owner, receiver))
                    python_bindings[owner][receiver] = (node_line(node), binding)

        for node in iter_nodes(tree.root_node):
            current = enclosing_symbol(node)
            text = node_text(node, source_file.content)

            if source_file.language.value == "JAVA":
                if node.type == "import_declaration":
                    target_name = text.strip().removeprefix("import").removeprefix("static").strip().rstrip(";")
                    imports.add(target_name)
                    add(current, target_name, RelationType.IMPORTS, node, text)
                elif node.type == "class_declaration":
                    superclass = node.child_by_field_name("superclass")
                    if superclass is not None:
                        target_name = node_text(superclass, source_file.content).removeprefix("extends ").strip()
                        target = resolver.resolve_name(target_name, current, imports)
                        add(current, target_name, RelationType.EXTENDS, superclass, node_text(superclass, source_file.content), target)
                    interfaces = node.child_by_field_name("interfaces")
                    if interfaces is not None:
                        for candidate in iter_nodes(interfaces):
                            if candidate.type in {"type_identifier", "identifier"}:
                                target_name = node_text(candidate, source_file.content)
                                target = resolver.resolve_name(target_name, current, imports)
                                add(current, target_name, RelationType.IMPLEMENTS, candidate, node_text(candidate, source_file.content), target)
                elif node.type == "method_invocation":
                    name_node = node.child_by_field_name("name")
                    if name_node is not None:
                        target_name = node_text(name_node, source_file.content)
                        receiver_node = node.child_by_field_name("object")
                        receiver = node_text(receiver_node, source_file.content) if receiver_node is not None else None
                        target, method = resolver.resolve_call_with_method(target_name, current, receiver, environment)
                        add(current, target_name, RelationType.CALLS, node, text, target, method)
                elif node.type == "type_identifier" and current is not None:
                    target_name = text
                    target = resolver.resolve_name(target_name, current, imports)
                    if target and target.id != current.id and target.type in {SymbolType.CLASS, SymbolType.INTERFACE}:
                        add(current, target_name, RelationType.REFERENCES, node, text, target)
            else:
                if node.type in {"import_statement", "import_from_statement"}:
                    target_name = text.strip()
                    imports.add(target_name.rsplit(" ", 1)[-1].removeprefix("import "))
                    add(current, target_name, RelationType.IMPORTS, node, text)
                elif node.type == "class_definition":
                    superclasses = node.child_by_field_name("superclasses")
                    if superclasses is not None:
                        for candidate in iter_nodes(superclasses):
                            if candidate.type in {"identifier", "attribute"}:
                                target_name = node_text(candidate, source_file.content)
                                target = resolver.resolve_name(target_name, current, imports)
                                add(current, target_name, RelationType.EXTENDS, candidate, target_name, target)
                elif node.type == "call":
                    function_node = node.child_by_field_name("function")
                    if function_node is not None:
                        target_name = node_text(function_node, source_file.content)
                        receiver = None
                        method_name = target_name
                        if function_node.type == "attribute":
                            object_node = function_node.child_by_field_name("object")
                            name_node = function_node.child_by_field_name("attribute")
                            receiver = node_text(object_node, source_file.content) if object_node else None
                            method_name = node_text(name_node, source_file.content) if name_node else target_name
                        bindings: dict[str, ReceiverBinding] = {}
                        if current:
                            for owner, known in ((current.parentSymbolId or "", class_bindings.get(current.parentSymbolId or "", {})),
                                                 (current.id, python_bindings.get(current.id, {}))):
                                for key, (assigned_line, bound) in known.items():
                                    if bound and (owner != current.id or assigned_line < node_line(node)) and \
                                            (owner, key) not in invalid_bindings:
                                        bindings[key] = bound
                        target, method = resolver.resolve_call_with_method(method_name, current, receiver, bindings)
                        add(current, method_name, RelationType.CALLS, node, text, target, method)

        return _deduplicate(result)


def _deduplicate(relations: list[Relation]) -> list[Relation]:
    seen: set[str] = set()
    output: list[Relation] = []
    for relation in relations:
        if relation.id in seen:
            continue
        seen.add(relation.id)
        output.append(relation)
    return output
