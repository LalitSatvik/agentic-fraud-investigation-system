# pipeline/

`run_batch.py` simulates transactions arriving: it pulls a sample of transactions, scores each
one through the API, and triggers the investigation agent on anything that crosses the risk
threshold — the same path a real streaming pipeline would take on each new transaction,
batched here for convenience rather than event-driven.

```bash
python pipeline/run_batch.py --num 20
```

Requires the API to be running with `ANTHROPIC_API_KEY` set.
