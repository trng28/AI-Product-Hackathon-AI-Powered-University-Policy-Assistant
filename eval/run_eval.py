from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.policy_assistant.service import PolicyAssistant  # noqa: E402


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text)


def score_result(case: dict, result: dict) -> dict:
    answer = normalize(result.get("answer", ""))
    citations = result.get("citations", [])
    expected_evidence = case["expect_evidence"]
    evidence_ok = result.get("evidence_sufficient") is expected_evidence

    groups = case.get("keyword_groups", [])
    group_hits = [
        any(normalize(option) in answer for option in alternatives)
        for alternatives in groups
    ]
    keyword_score = sum(group_hits) / len(group_hits) if group_hits else 1.0

    if expected_evidence:
        expected_sources = [
            normalize(value) for value in case.get("expected_sources", []) if value
        ]
        expected_article = normalize(case.get("expected_article", ""))
        expected_pages = set(case.get("expected_pages", []))

        def matches(citation: dict) -> bool:
            haystack = normalize(
                " ".join(
                    str(citation.get(key, ""))
                    for key in ("article", "clause", "document", "source_url")
                )
            )
            source_ok = (
                any(source in haystack for source in expected_sources)
                if expected_sources
                else expected_article in normalize(citation.get("article", ""))
            )
            page_ok = (
                citation.get("page") in expected_pages if expected_pages else True
            )
            return source_ok and page_ok

        citation_ok = any(matches(citation) for citation in citations)
    else:
        citation_ok = len(citations) == 0

    score = (
        0.45 * keyword_score
        + 0.30 * float(citation_ok)
        + 0.20 * float(evidence_ok)
        + 0.05 * float(bool(result.get("answer")))
    )
    return {
        "keyword_score": round(keyword_score, 3),
        "keyword_group_hits": group_hits,
        "citation_ok": citation_ok,
        "evidence_ok": evidence_ok,
        "score": round(score, 3),
        "passed": score >= 0.75 and citation_ok and evidence_ok,
    }


def write_report(payload: dict, path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Báo cáo Eval – VinUni Policy Assistant",
        "",
        f"- Thời gian: {payload['run_at']}",
        f"- Provider/model: `{payload['provider']}` / `{payload['model']}`",
        f"- Tổng số câu: **{summary['total']}**",
        f"- Chạy thành công: **{summary['completed']}**",
        f"- Passed: **{summary['passed']}** ({summary['pass_rate']:.1%})",
        f"- Điểm trung bình: **{summary['average_score']:.1%}**",
        f"- Citation accuracy: **{summary['citation_accuracy']:.1%}**",
        f"- Evidence decision accuracy: **{summary['evidence_accuracy']:.1%}**",
        f"- Thời gian trung bình/câu: **{summary['average_latency_seconds']:.2f}s**",
        "",
        "## Kết quả chi tiết",
        "",
        "| ID | Category | Score | Pass | Citation | Evidence | Latency |",
        "|---|---|---:|:---:|:---:|:---:|---:|",
    ]
    for item in payload["results"]:
        grading = item.get("grading", {})
        lines.append(
            f"| {item['id']} | {item['category']} | "
            f"{grading.get('score', 0):.0%} | "
            f"{'✅' if grading.get('passed') else '❌'} | "
            f"{'✅' if grading.get('citation_ok') else '❌'} | "
            f"{'✅' if grading.get('evidence_ok') else '❌'} | "
            f"{item['latency_seconds']:.2f}s |"
        )
    failures = [item for item in payload["results"] if not item.get("grading", {}).get("passed")]
    lines.extend(["", "## Các trường hợp chưa đạt", ""])
    if not failures:
        lines.append("Không có.")
    for item in failures:
        lines.extend(
            [
                f"### {item['id']} – {item['input']}",
                "",
                f"- Expected: {item['expected_behavior']}",
                f"- Error: {item.get('error') or 'Không có'}",
                f"- Answer: {item.get('output', {}).get('answer', '')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize(results: list[dict]) -> dict:
    if not results:
        return {
            "total": 0,
            "completed": 0,
            "passed": 0,
            "pass_rate": 0,
            "average_score": 0,
            "citation_accuracy": 0,
            "evidence_accuracy": 0,
            "average_latency_seconds": 0,
        }
    return {
        "total": len(results),
        "completed": sum(not item.get("error") for item in results),
        "passed": sum(item["grading"]["passed"] for item in results),
        "pass_rate": mean(item["grading"]["passed"] for item in results),
        "average_score": mean(item["grading"]["score"] for item in results),
        "citation_accuracy": mean(item["grading"]["citation_ok"] for item in results),
        "evidence_accuracy": mean(item["grading"]["evidence_ok"] for item in results),
        "average_latency_seconds": mean(item["latency_seconds"] for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("questions.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument(
        "--regrade",
        type=Path,
        help="Regrade a prior raw result without calling the agent again.",
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    cases = dataset["questions"][: args.limit]
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.regrade:
        payload = json.loads(args.regrade.read_text(encoding="utf-8"))
        cases_by_id = {case["id"]: case for case in cases}
        for item in payload["results"]:
            case = cases_by_id[item["id"]]
            item["expected_behavior"] = case["expected_behavior"]
            item["grading"] = score_result(case, item.get("output", {}))
        payload["dataset_version"] = dataset["version"]
        payload["regraded_at"] = datetime.now(timezone.utc).isoformat()
        payload["summary"] = summarize(payload["results"])
        latest_json = output_dir / "latest.json"
        latest_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_report(payload, output_dir / "latest.md")
        print(f"Regraded: {latest_json}")
        critical_failed = any(
            cases_by_id[item["id"]].get("critical", False)
            and not item["grading"]["passed"]
            for item in payload["results"]
        )
        return 0 if (
            payload["summary"]["pass_rate"] >= args.min_pass_rate
            and not critical_failed
        ) else 1

    assistant = PolicyAssistant()
    results = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}: {case['input']}", flush=True)
        started = time.perf_counter()
        item = {key: case[key] for key in ("id", "category", "input", "expected_behavior")}
        try:
            output = assistant.ask(case["input"]).to_dict()
            item["output"] = output
            item["grading"] = score_result(case, output)
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            item["output"] = {}
            item["grading"] = {
                "score": 0,
                "passed": False,
                "citation_ok": False,
                "evidence_ok": False,
                "keyword_score": 0,
            }
        item["latency_seconds"] = round(time.perf_counter() - started, 3)
        results.append(item)
        print(
            f"  -> score={item['grading']['score']:.0%}, "
            f"pass={item['grading']['passed']}, "
            f"{item['latency_seconds']:.2f}s",
            flush=True,
        )

    summary = summarize(results)
    settings = assistant.settings
    payload = {
        "dataset": dataset["name"],
        "dataset_version": dataset["version"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.provider,
        "model": settings.model,
        "summary": summary,
        "results": results,
    }
    critical_failed = any(
        case.get("critical", False) and not result["grading"]["passed"]
        for case, result in zip(cases, results)
    )
    payload["quality_gate"] = {
        "minimum_pass_rate": args.min_pass_rate,
        "critical_failed": critical_failed,
        "passed": summary["pass_rate"] >= args.min_pass_rate and not critical_failed,
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = output_dir / f"eval-{stamp}.json"
    report_path = output_dir / f"eval-{stamp}.md"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload, report_path)
    (output_dir / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(payload, output_dir / "latest.md")
    print(f"\nRaw: {raw_path}\nReport: {report_path}")
    return 0 if payload["quality_gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
