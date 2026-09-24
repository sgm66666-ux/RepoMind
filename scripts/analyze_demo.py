"""Run the repository analysis and deterministic fault-localization demo."""

import json
from pathlib import Path

from app.domain.models import to_dict
from app.fault.localizer import FaultLocalizer
from app.repository.index import AnalysisIndex


def main() -> None:
    repository = Path(__file__).parents[1] / "demo" / "order-demo"
    index = AnalysisIndex().analyze(repository)
    calls = []
    for symbol in index.symbols.values():
        for edge in index.callGraph.findCallees(symbol.id):
            calls.append({"from": symbol.qualifiedName, "to": edge["symbol"].qualifiedName})
    fault = FaultLocalizer(index).localize((repository / "expected-stacktrace.txt").read_text(encoding="utf-8"))
    print(json.dumps({
        "repository": str(repository),
        "sourceFileCount": len(index.sourceFiles),
        "symbolCount": len(index.symbols),
        "relationCount": len(index.relations),
        "resolvedCallCount": len(calls),
        "callGraph": calls,
        "faultLocalization": to_dict(fault),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
