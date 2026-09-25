"""Classify each unresolved enterprise-showcase CALLS relation for review.

This is a showcase-specific audit, not a resolver or benchmark rule. Unknown
patterns fail closed so a new relation cannot silently enter a category.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from app.domain.models import RelationType, SourceFile
from app.repository.index import AnalysisIndex
from app.repository.scanner import RepositoryScanner, ScanResult


JDK_PREFIXES = (
    "List.", "UUID.", "BigDecimal.", "Instant.", "System.out.", '"WALLET".',
    "items.", "records.", "outbox.", "customers.", "stockBySku.",
    "orders.", "payments.", "products.", "promotions.",
    "product.getPrice().multiply", "record.getOrderId().equals",
    "response.getTotal().isBlank",
)


def classify(relation, index) -> tuple[str, str, str]:
    code = relation.evidence.strip()
    name = relation.targetName
    filename = Path(relation.filePath).name
    if filename == "OrderFlowTest.java" and name in {"assertEquals", "assertNotNull", "assertFalse"}:
        return "EXTERNAL_LIBRARY", "LEGITIMATELY_UNRESOLVED", "JUnit assertion is outside the source index"
    if code.startswith("new StockAllocator(") and name == "allocate":
        return "CONSTRUCTOR_CREATED_RECEIVER", "RESOLVABLE_GAP", "constructor result type is not propagated"
    if code == "record.getOrderId()" and name == "getOrderId":
        return "LAMBDA_RECEIVER_UNKNOWN", "RESOLVABLE_GAP", "stream lambda parameter type is not inferred"
    if (code.startswith("Money.of(") and name == "of") or (
            code.startswith("ShowcaseApplication.createController(") and name == "createController"):
        return "STATIC_CLASS_RECEIVER", "RESOLVABLE_GAP", "indexed class receiver can be checked conservatively"
    if filename == "Money.java" and code.startswith("amount."):
        return "JDK_LIBRARY", "LEGITIMATELY_UNRESOLVED", "BigDecimal receiver is outside the project index"
    if code.startswith("amount.amount().signum()") and name == "signum":
        return "JDK_LIBRARY", "LEGITIMATELY_UNRESOLVED", "BigDecimal signum is outside the project index"
    if code.startswith(JDK_PREFIXES) or (code.startswith("UUID.randomUUID().") and name == "toString"):
        return "JDK_LIBRARY", "LEGITIMATELY_UNRESOLVED", "receiver belongs to the JDK, not the project Symbol index"
    if name == "valueOf" and code.startswith("BigDecimal."):
        return "JDK_LIBRARY", "LEGITIMATELY_UNRESOLVED", "BigDecimal is outside the project index"
    if ")." in code:
        return "CHAINED_PROJECT_CALL", "RESOLVABLE_GAP", "project-local return type is not propagated through a call chain"
    project_methods = [symbol for symbol in index.symbols.values() if
                       symbol.name == name and symbol.type.value == "METHOD"]
    if project_methods:
        return "SCOPED_RECEIVER_TYPE", "RESOLVABLE_GAP", "project method exists, but local/parameter receiver was not bound"
    raise ValueError(f"Unclassified CALLS relation: {filename}:{relation.line} {code}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline-inventory-source", action="store_true",
                        help="Reconstruct the pre-guard inventory method in memory for the recorded baseline")
    args = parser.parse_args()
    if args.baseline_inventory_source:
        scan = RepositoryScanner().scan(args.repository)
        replacement = ("    @Override public Stock findAvailableStock(String sku) {\n"
                       "        Stock stock = stockBySku.get(sku);\n"
                       "        if (stock == null) return null;\n"
                       "        return stock;\n"
                       "    }")
        original = "    @Override public Stock findAvailableStock(String sku) { return stockBySku.get(sku); }"
        matches = [item for item in scan.files if item.filePath.endswith("/InMemoryInventoryRepository.java")]
        if len(matches) != 1 or matches[0].content.count(replacement) != 1:
            raise ValueError("Cannot reconstruct the recorded inventory source baseline")
        files = [SourceFile(item.filePath, item.language, item.content.replace(replacement, original))
                 if item is matches[0] else item for item in scan.files]
        with patch.object(RepositoryScanner, "scan", return_value=ScanResult(files, scan.issues)):
            index = AnalysisIndex().analyze(args.repository)
    else:
        index = AnalysisIndex().analyze(args.repository)
    unresolved = [item for item in index.relations if item.type == RelationType.CALLS and not item.resolved]
    records = []
    for relation in unresolved:
        category, disposition, reason = classify(relation, index)
        records.append({"relationId": relation.id, "file": relation.filePath,
                        "line": relation.line, "sourceSymbolId": relation.sourceSymbolId,
                        "targetName": relation.targetName, "code": relation.evidence,
                        "category": category, "disposition": disposition, "reason": reason})
    summary = {"sourceFiles": len(index.sourceFiles), "symbols": len(index.symbols),
               "relations": len(index.relations),
               "resolvedCalls": sum(item.type == RelationType.CALLS and item.resolved for item in index.relations),
               "unresolvedCalls": len(unresolved),
               "categories": dict(sorted(Counter(item["category"] for item in records).items())),
               "dispositions": dict(sorted(Counter(item["disposition"] for item in records).items()))}
    report = {"summary": summary, "unresolved": records}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
