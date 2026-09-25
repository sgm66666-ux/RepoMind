"""Record three real local Ollama Agent runs; never synthesize missing evidence."""

import argparse
import json
import urllib.request
from pathlib import Path


QUESTION = "为什么订单创建流程在 StockAllocator.allocate 库存预留阶段可能出现 NullPointerException？"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:28100")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = []
    for number in range(1, 4):
        payload = json.dumps({"question": QUESTION, "maxSteps": 8, "timeoutSeconds": 180},
                             ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(args.base_url.rstrip("/") + "/agent/chat", data=payload,
                                         headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.load(response)
        provider = result.get("provider", "")
        if not provider.startswith("ollama:qwen2.5-coder:14b:"):
            raise RuntimeError(f"Run {number}: real local Ollama provider was not used: {provider}")
        trace = result.get("trace") or []
        files_read = [step["observation"]["data"]["filePath"] for step in trace if
                      step.get("tool") == "readFile" and step.get("success") and
                      isinstance(step.get("observation", {}).get("data"), dict)]
        execution = result.get("executionState") or {}
        diagnosis = result.get("finalDiagnosis")
        chain = result.get("crossFileEvidence") or execution.get("cross_file_evidence") or {}
        record = {"run": number, "question": QUESTION, "provider": provider,
                  "status": result.get("status"), "diagnosisStatus": result.get("diagnosisStatus"),
                  "completionDecision": result.get("completionDecision"),
                  "trace": [{"step": step.get("step"), "tool": step.get("tool"),
                             "input": step.get("input"), "success": step.get("success"),
                             "progress": step.get("progress"), "policyStatus": step.get("policyStatus")}
                            for step in trace],
                  "filesRead": files_read,
                  "graphEvidence": execution.get("graph_path_evidence"),
                  "verifiedEvidenceCounts": execution.get("verified_evidence_counts"),
                  "crossFileEvidence": chain,
                  "finalDiagnosis": diagnosis,
                  "rawModelOutput": result.get("rawModelOutput"),
                  "diagnosisIssues": result.get("diagnosisIssues"),
                  "evidenceProjection": result.get("evidenceProjection")}
        runs.append(record)
        print(f"run={number} status={record['status']} diagnosis={record['diagnosisStatus']} "
              f"crossFileFinal={chain.get('final_diagnosis_complete', False)} "
              f"tools={' -> '.join(item['tool'] or '?' for item in record['trace'])} "
              f"files={files_read}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
