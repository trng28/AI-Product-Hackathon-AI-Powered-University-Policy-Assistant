"""Deterministic retrieval quality gate for the processed public policies."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate FAISS retrieval against all public policy topics."
    )
    parser.add_argument("--index", type=Path, default=PROJECT_ROOT / "data/policy-index")
    parser.add_argument(
        "--processed",
        type=Path,
        default=PROJECT_ROOT / "src/data/vinuni-policies/processed",
    )
    parser.add_argument(
        "--cases", type=Path, default=Path(__file__).with_name("retrieval_cases.json")
    )
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--min-recall", type=float, default=0.85)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    import faiss

    config = json.loads((args.index / "config.json").read_text(encoding="utf-8"))
    indexed = json.loads((args.index / "chunks.json").read_text(encoding="utf-8"))
    policies = load_jsonl(args.processed / "policies.jsonl")
    internal = load_jsonl(args.processed / "internal_policies.jsonl")
    robustness = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]

    # One deterministic topic-coverage case for every public policy.
    coverage = [
        {
            "id": f"C{index:02d}",
            "category": "topic_coverage",
            "query": f"Quy định và nội dung của tài liệu {policy['title']} là gì?",
            "expected_reference": policy["metadata"].get("reference_number", ""),
            "expected_title": policy["title"],
        }
        for index, policy in enumerate(policies, start=1)
    ]
    cases = [*coverage, *robustness]

    model = SentenceTransformer(config["embedding_model"])
    vectors = model.encode(
        [f"query: {case['query']}" for case in cases],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")
    index = faiss.read_index(str(args.index / "vectors.faiss"))
    _, ids = index.search(np.asarray(vectors), min(args.top_k, len(indexed)))

    results = []
    category_hits: dict[str, list[bool]] = defaultdict(list)
    reciprocal_ranks = []
    for case, result_ids in zip(cases, ids):
        hits = [indexed[int(item)] for item in result_ids if item >= 0]
        expected_reference = normalize(case.get("expected_reference", ""))
        expected_title = normalize(case.get("expected_title", ""))

        def relevant(chunk: dict) -> bool:
            article = normalize(chunk.get("article", ""))
            clause = normalize(chunk.get("clause", ""))
            return bool(
                (expected_reference and expected_reference in clause)
                or (expected_title and expected_title in article)
            )

        rank = next(
            (position for position, chunk in enumerate(hits, start=1) if relevant(chunk)),
            None,
        )
        passed = rank is not None
        category_hits[case["category"]].append(passed)
        reciprocal_ranks.append(1 / rank if rank else 0)
        results.append(
            {
                **case,
                "passed": passed,
                "rank": rank,
                "retrieved": [
                    {
                        "article": chunk["article"],
                        "reference": chunk["clause"],
                        "chunk_id": chunk["id"],
                    }
                    for chunk in hits
                ],
            }
        )

    internal_ids = {item["id"] for item in internal}
    leaked = [
        chunk["id"]
        for chunk in indexed
        if chunk["id"].rsplit("-", 1)[0] in internal_ids
    ]
    recall = sum(item["passed"] for item in results) / len(results)
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "topic_coverage_cases": len(coverage),
        "robustness_cases": len(robustness),
        "recall_at_k": recall,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "top_k": args.top_k,
        "min_recall": args.min_recall,
        "internal_chunks_leaked": len(leaked),
        "by_category": {
            category: sum(values) / len(values)
            for category, values in sorted(category_hits.items())
        },
    }
    passed_gate = recall >= args.min_recall and not leaked
    payload = {"summary": summary, "passed": passed_gate, "results": results}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "retrieval-latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failures = [item for item in results if not item["passed"]]
    for item in failures:
        print(f"FAIL {item['id']}: {item['query']}")
        print(f"  expected: {item.get('expected_reference') or item.get('expected_title')}")
        print(f"  top-1: {item['retrieved'][0] if item['retrieved'] else 'none'}")
    print("QUALITY GATE:", "PASS" if passed_gate else "FAIL")
    return 0 if passed_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
