"""
Runs the gold-standard evaluation: for each case, triggers a real
investigation via the API, scores it deterministically against the gold
expectation (recommendation within the acceptable set? did it violate a
must-not-recommend trap? did it use all four tools?), and grades report
quality with the LLM rubric judge.

Costs real API calls (one investigation + one judge call per case) — use
--limit / --categories to control spend while iterating.

Requires the API running (api/main.py) with ANTHROPIC_API_KEY set, and must
run under the agent environment (needs claude_agent_sdk for the judge).

Run:
    python eval/run_eval.py --limit 5
    python eval/run_eval.py --categories clean_fraud_ring ambiguous_legit
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.scorers.rubric_judge import grade  # noqa: E402

GOLD_SET_PATH = ROOT / "eval" / "gold_set" / "gold_set.json"
RESULTS_DIR = ROOT / "eval" / "results"
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
REQUIRED_TOOLS = {"customer_history", "geo_ip_lookup", "graph_features", "reputation_check"}


def evaluate_case(client: httpx.Client, case: dict) -> dict:
    txn_id = case["transaction_id"]
    resp = client.post(f"/investigations/{txn_id}/run")
    if resp.status_code != 200:
        return {**case, "error": f"investigation failed ({resp.status_code}): {resp.text[:500]}"}

    inv = resp.json()
    report = inv.get("report")
    if report is None:
        return {**case, "error": "agent produced no structured report", "report_error": inv.get("report_error")}

    recommended = report.get("recommended_action")
    recommendation_ok = recommended in case["expected_action_set"]
    violated_must_not = bool(case.get("must_not_recommend") and recommended == case["must_not_recommend"])

    text_blob = " ".join(
        [report.get("rationale", ""), report.get("summary", "")]
        + [f.get("factor", "") + " " + f.get("evidence", "") for f in report.get("risk_factors", [])]
        + report.get("mitigating_factors", [])
    ).lower()
    keywords = case.get("expected_evidence_keywords", [])
    keyword_hits = [k for k in keywords if k.lower() in text_blob]
    evidence_keyword_coverage = (len(keyword_hits) / len(keywords)) if keywords else None

    tools_consulted = set(report.get("tools_consulted", []))
    all_four_tools_used = tools_consulted >= REQUIRED_TOOLS

    judge_result = grade(case, report, inv.get("trace") or [])

    return {
        **case,
        "investigation_id": inv["id"],
        "recommended_action": recommended,
        "confidence": report.get("confidence"),
        "recommendation_ok": recommendation_ok,
        "violated_must_not_recommend": violated_must_not,
        "all_four_tools_used": all_four_tools_used,
        "evidence_keyword_coverage": evidence_keyword_coverage,
        "evidence_keyword_hits": keyword_hits,
        "total_cost_usd": inv.get("total_cost_usd"),
        "judge": judge_result,
    }


def main(limit, categories) -> None:
    cases = json.loads(GOLD_SET_PATH.read_text())
    if categories:
        cases = [c for c in cases if c["category"] in categories]
    if limit:
        cases = cases[:limit]
    if not cases:
        print("No gold cases matched the given filters.")
        return

    client = httpx.Client(base_url=API_BASE_URL, timeout=200.0)
    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['transaction_id']} ({case['category']})...")
        result = evaluate_case(client, case)
        results.append(result)
        if result.get("error"):
            status = "ERROR"
        elif result.get("violated_must_not_recommend"):
            status = "VIOLATION"
        elif result.get("recommendation_ok"):
            status = "OK"
        else:
            status = "MISS"
        judge = result.get("judge") or {}
        print(f"    -> {status}  recommended={result.get('recommended_action')}  judge_score={judge.get('overall_score')}")

    RESULTS_DIR.mkdir(exist_ok=True, parents=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"eval_{ts}.json"
    out_path.write_text(json.dumps(results, indent=2))

    n = len(results)
    scored = [r for r in results if not r.get("error")]
    n_ok = sum(1 for r in scored if r.get("recommendation_ok"))
    n_violation = sum(1 for r in scored if r.get("violated_must_not_recommend"))
    n_tools_ok = sum(1 for r in scored if r.get("all_four_tools_used"))
    judge_scores = [r["judge"]["overall_score"] for r in scored if isinstance(r.get("judge"), dict) and "overall_score" in r["judge"]]
    avg_judge = round(sum(judge_scores) / len(judge_scores), 2) if judge_scores else None
    total_cost = sum(r.get("total_cost_usd") or 0 for r in scored)

    print(f"\n=== Summary ({n} cases, {len(scored)} scored, {n - len(scored)} errored) ===")
    if scored:
        print(f"Recommendation within expected set: {n_ok}/{len(scored)} ({n_ok/len(scored):.0%})")
        print(f"Violated must-not-recommend (costly errors): {n_violation}/{len(scored)}")
        print(f"Used all 4 tools: {n_tools_ok}/{len(scored)}")
        print(f"Avg judge overall_score (1-5): {avg_judge}")
    print(f"Total investigation cost: ${total_cost:.4f}")
    print(f"\nFull results: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--categories", nargs="*", default=None)
    args = parser.parse_args()
    main(args.limit, args.categories)
