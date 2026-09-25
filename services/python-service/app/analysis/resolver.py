from collections import defaultdict
from dataclasses import dataclass

from app.domain.models import Language, Symbol, SymbolType


@dataclass(frozen=True)
class ReceiverBinding:
    """A class established by an AST constructor assignment, not a name guess."""

    class_symbol_id: str
    resolution_method: str


class SymbolResolver:
    """Conservative resolver: ambiguity stays unresolved."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self.symbols = symbols
        qualified: dict[str, list[Symbol]] = defaultdict(list)
        for symbol in symbols:
            qualified[symbol.qualifiedName].append(symbol)
        # Do not arbitrarily choose an overload with the same qualified name.
        self.by_qualified = {name: values[0] for name, values in qualified.items() if len(values) == 1}
        self.by_id = {symbol.id: symbol for symbol in symbols}
        self.by_name: dict[str, list[Symbol]] = defaultdict(list)
        for symbol in symbols:
            self.by_name[symbol.name].append(symbol)

    def resolve_name(
        self,
        target_name: str,
        current_symbol: Symbol | None,
        imports: set[str] | None = None,
    ) -> Symbol | None:
        candidate = self.by_qualified.get(target_name)
        if candidate:
            return candidate

        if imports:
            imported = [item for item in imports if item.rsplit(".", 1)[-1] == target_name]
            if len(imported) > 1:
                return None
            if imported:
                candidate = self.by_qualified.get(imported[0])
                if candidate:
                    return candidate

        if current_symbol:
            parts = current_symbol.qualifiedName.split(".")
            for index in range(len(parts), 0, -1):
                candidate = self.by_qualified.get(".".join(parts[:index] + [target_name]))
                if candidate:
                    return candidate

        candidates = self.by_name.get(target_name, [])
        return candidates[0] if len(candidates) == 1 else None

    def resolve_call(
        self,
        method_name: str,
        current_symbol: Symbol | None,
        receiver: str | None = None,
        type_environment: dict[str, str | ReceiverBinding] | None = None,
    ) -> Symbol | None:
        return self.resolve_call_with_method(method_name, current_symbol, receiver, type_environment)[0]

    def resolve_call_with_method(
        self,
        method_name: str,
        current_symbol: Symbol | None,
        receiver: str | None = None,
        type_environment: dict[str, str | ReceiverBinding] | None = None,
        imports: set[str] | None = None,
    ) -> tuple[Symbol | None, str]:
        type_environment = type_environment or {}
        receiver = receiver.removeprefix("this.") if receiver else None

        if receiver in {"this", "self"} and current_symbol and current_symbol.parentSymbolId:
            owner = self.by_id.get(current_symbol.parentSymbolId)
            if owner:
                target = self.by_qualified.get(f"{owner.qualifiedName}.{method_name}")
                if target and target.type == SymbolType.METHOD:
                    return target, "DIRECT_SYMBOL"

        if receiver:
            binding = type_environment.get(receiver)
            if isinstance(binding, ReceiverBinding):
                owner = self.by_id.get(binding.class_symbol_id)
                classes = [owner] if owner and owner.type in {SymbolType.CLASS, SymbolType.INTERFACE} else []
                method = binding.resolution_method
            elif isinstance(binding, str):
                classes = [
                    symbol
                    for symbol in self.by_name.get(binding, [])
                    if symbol.type in {SymbolType.CLASS, SymbolType.INTERFACE}
                ]
                method = "RECEIVER_TYPE_BINDING"
            else:
                classes = []
                method = "UNRESOLVED"
            if len(classes) == 1:
                target = self.by_qualified.get(f"{classes[0].qualifiedName}.{method_name}")
                if target and target.type == SymbolType.METHOD:
                    return target, method
            if not classes and current_symbol and current_symbol.language == Language.JAVA and "." not in receiver:
                # Java permits ClassName.staticMethod(); only a uniquely indexed
                # class and a non-overloaded method are safe to bind here.
                owners = [item for item in self.by_name.get(receiver, []) if item.type == SymbolType.CLASS]
                if len(owners) == 1 and (owners[0].filePath == current_symbol.filePath or
                                         owners[0].module == current_symbol.module or
                                         owners[0].qualifiedName in (imports or set()) or
                                         f"{owners[0].module}.*" in (imports or set())):
                    target = self.by_qualified.get(f"{owners[0].qualifiedName}.{method_name}")
                    if target and target.type == SymbolType.METHOD:
                        return target, "STATIC_CLASS_RECEIVER"
            return None, "UNRESOLVED"

        if current_symbol:
            owner = current_symbol
            if owner.type == SymbolType.METHOD and owner.parentSymbolId:
                owner = self.by_id.get(owner.parentSymbolId, owner)
            qualified = f"{owner.qualifiedName}.{method_name}"
            target = self.by_qualified.get(qualified)
            if target:
                return target, "DIRECT_SYMBOL"

        candidates = [
            symbol
            for symbol in self.by_name.get(method_name, [])
            if (symbol.type == SymbolType.FUNCTION if current_symbol and current_symbol.language == Language.PYTHON
                else symbol.type in {SymbolType.METHOD, SymbolType.FUNCTION})
        ]
        if current_symbol and current_symbol.language == Language.PYTHON:
            same_module = [symbol for symbol in candidates if symbol.module == current_symbol.module]
            if len(same_module) == 1:
                return same_module[0], "DIRECT_SYMBOL"
        return (candidates[0], "DIRECT_SYMBOL") if len(candidates) == 1 else (None, "UNRESOLVED")
