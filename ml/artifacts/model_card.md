# Model Card — Base Fraud Classifier

- **Algorithm**: XGBoost (`n_estimators=400`, `max_depth=5`), time-ordered train/val/test split
  (70/15/15 by simulation `step`) to avoid leaking future transactions into training.
- **Companion signal**: IsolationForest (unsupervised), reported for context — not used to set
  the operating threshold. ROC-AUC alone on test: 0.8400.
- **Features**: transaction-level + causal customer-history aggregates only (see
  `feature_columns.json`). Deliberately excludes geo/IP/device/graph/merchant-reputation
  enrichment — those are reserved for the Investigation Agent's tools post-flagging.
- **Operating threshold**: 0.5250, chosen as the highest threshold on
  the validation set that still clears 85% recall (missing fraud is costlier than a false
  positive here — false positives get reviewed by the Investigation Agent + human, not
  auto-declined).
- **Test performance**: PR-AUC 1.0000, ROC-AUC 1.0000,
  precision 1.000, recall 0.970 at the chosen
  threshold. Confusion matrix: {'tn': 19758, 'fp': 0, 'fn': 121, 'tp': 3853}.
- **Top features by importance**: error_balance_orig (0.506), amount_to_orig_balance_ratio (0.170), orig_balance_after (0.162), balance_delta_orig (0.108), hour_of_day (0.011).
- **Known limitations**: trained on a downsampled PaySim (5.2% fraud rate vs PaySim's native
  0.13%), so absolute precision numbers won't transfer to production traffic without
  recalibration; balance-consistency features are strong in PaySim specifically because its
  simulator doesn't perfectly conserve balances on fraudulent transfers, which may not hold on
  real payment rails.
- **Discrete-looking risk scores**: because 4 balance-consistency features carry ~95% of total
  importance and PaySim's simulator makes those features near-binary, `predict_proba` collapses
  to a handful of distinct values (spot-checked: 4 unique scores across 30 random legit
  transactions, all comfortably below threshold) rather than a smooth distribution. This is
  real tree-ensemble behavior on this specific dataset, not a scoring bug — verified by manual
  inspection of `ml/scoring.py` output. Worth keeping in mind: this base model is close to a
  rule-of-thumb balance check for PaySim specifically; the Investigation Agent's job of pulling
  in independent evidence (geo, device, history, graph) matters more here than it would for a
  model with smoother, more feature-diverse scores.
