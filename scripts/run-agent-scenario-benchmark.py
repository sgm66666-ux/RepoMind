"""Call the running real FastAPI/Ollama Agent; do not substitute expected observations."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "python-service"))

from app.evaluation.agent_scenario_benchmark import evaluate_scenario, render_markdown, summarize  # noqa: E402
from app.evaluation.execution_policy_comparison import build_comparison, render_comparison  # noqa: E402
from app.evaluation.evidence_projection_comparison import compare_evidence, render_evidence_comparison  # noqa: E402
from app.evaluation.scenario_models import REPETITION_IDS, SCENARIOS  # noqa: E402


def post_json(base_url: str, path: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        base_url + path, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def write_report(report: dict, output_dir: Path, output_stem: str,
                 before_report: dict | None = None, evidence_projection: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report["summary"] = summarize(report["results"])
    report["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    if before_report is not None:
        report["comparison"] = build_comparison(before_report, report)
        if evidence_projection:
            report["evidence_comparison"] = compare_evidence(before_report, report)
    json_path = output_dir / f"{output_stem}.json"
    markdown_path = output_dir / f"{output_stem}.md"
    temporary = json_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(json_path)
    markdown = render_markdown(report)
    if before_report is not None:
        markdown += "\n\n" + render_comparison(report["comparison"])
        if evidence_projection:
            markdown += "\n\n" + render_evidence_comparison(report["evidence_comparison"])
    markdown_path.write_text(markdown, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:19002")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "evaluation")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-stem", default="agent-scenario-benchmark")
    parser.add_argument("--before-report", type=Path,
                        help="Frozen prior JSON report to compare; never modified")
    parser.add_argument("--evidence-projection", action="store_true",
                        help="Add Observation-backed evidence/projection comparison")
    parser.add_argument("--rescore", action="store_true",
                        help="Re-evaluate saved real API responses without making new model calls")
    args = parser.parse_args()
    if args.repetitions < 0:
        parser.error("--repetitions must be >= 0")
    base_url = args.base_url.rstrip("/")
    if not args.output_stem or any(char in args.output_stem for char in "/\\:"):
        parser.error("--output-stem must be a plain filename stem")
    scenario_by_id = {item.id: item for item in SCENARIOS}
    before_report = json.loads(args.before_report.read_text(encoding="utf-8")) if args.before_report else None
    if args.rescore:
        report_path = args.output_dir / f"{args.output_stem}.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rescored = []
        for old in report["results"]:
            result = evaluate_scenario(scenario_by_id[old["scenario_id"]],
                                       old.get("full_response"), old.get("http_error"))
            result.update(run_group=old["run_group"], run_index=old["run_index"],
                          analysis=old.get("analysis"), captured_at=old["captured_at"])
            rescored.append(result)
        report["results"] = rescored
        report["evaluation_note"] = "Rescored the saved real API responses with current post-hoc metrics; no new Agent or LLM calls."
        write_report(report, args.output_dir, args.output_stem, before_report, args.evidence_projection)
        print(f"Rescored {len(rescored)} saved real calls; no model calls made.", flush=True)
        return
    report = {"generated_at": None, "api_base_url": base_url, "model": "qwen2.5-coder:14b",
              "method": "serial real FastAPI /analysis/repository + /agent/chat; no mock provider",
              "results": []}
    if (args.output_dir / f"{args.output_stem}.json").exists():
        parser.error("Report already exists; choose a new --output-stem to preserve prior runs")
    schedule = [("baseline", 1, scenario) for scenario in SCENARIOS]
    schedule.extend(("repeat", repeat, scenario_by_id[scenario_id])
                    for scenario_id in REPETITION_IDS for repeat in range(1, args.repetitions + 1))
    for number, (group, index, scenario) in enumerate(schedule, 1):
        print(f"[{number}/{len(schedule)}] {group} #{index} {scenario.id}", flush=True)
        response = None
        error = None
        analysis = None
        try:
            analysis = post_json(base_url, "/analysis/repository",
                                 {"path": str(ROOT / scenario.repository_path)}, 30)
            if analysis.get("analysisReady") is not True:
                raise ValueError("Repository analysis did not report analysisReady=true; Agent call skipped")
            response = post_json(base_url, "/agent/chat",
                                 {"question": scenario.user_query, "maxSteps": 8,
                                  "timeoutSeconds": 180}, 210)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1500]
            error = f"HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        result = evaluate_scenario(scenario, response, error)
        result.update(run_group=group, run_index=index, analysis=analysis,
                      captured_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"))
        report["results"].append(result)
        write_report(report, args.output_dir, args.output_stem, before_report, args.evidence_projection)
        print(f"    {result['final_status']} | {result['diagnosis_status']} | "
              f"tools={','.join(result['tools_used']) or '-'} | error={error or '-'}", flush=True)
    print(f"Report: {args.output_dir / (args.output_stem + '.md')}", flush=True)


if __name__ == "__main__":
    main()
