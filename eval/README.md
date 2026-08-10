# eval/

Evaluates the investigation agent's report quality against a curated gold-standard set, rather
than relying on spot-checks.

## Contents

- `gold_set/build_gold_set.py` — curates 20 cases (4 each across 5 categories) from the dataset's
  known ground truth: confirmed-fraud ring-linked cases, confirmed-fraud account-takeover cases,
  clean legitimate cases, and two adversarial categories designed to catch specific failure
  modes — a legitimate transaction with surface-level red flags (false-positive trap) and a
  confirmed-fraud transaction with no surface-level red flags, relying on history/graph signal
  instead (false-negative trap).
- `scorers/rubric_judge.py` — an LLM-as-judge rubric scorer, run as a separate, non-agentic call
  so grading isn't influenced by the same tool-calling context that produced the report. Scores
  evidence completeness, reasoning quality, and hallucination — separately from whether the
  final recommendation was correct, which is checked deterministically.
- `run_eval.py` — runs each gold case through a real investigation, checks the recommendation
  against the case's expected outcome (and flags `must_not_recommend` violations as the more
  serious failure category), and grades the report with the rubric judge. Writes a full results
  file and a summary to `results/`.

## Running

```bash
python eval/run_eval.py --limit 5
python eval/run_eval.py --categories clean_fraud_ring ambiguous_legit
```

Each case costs one investigation and one judge call in real API usage.
