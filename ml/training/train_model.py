"""
Train the base fraud classifier (XGBoost) plus an optional unsupervised
IsolationForest anomaly detector, on a time-ordered split (train on earlier
`step`s, validate/test on later ones — avoids leaking the future into
training, and mirrors how this model would actually be deployed).

Outputs to ml/artifacts/:
    model.joblib            XGBoost classifier
    anomaly_model.joblib     IsolationForest
    feature_columns.json
    threshold.json           chosen operating threshold + rationale
    metrics.json
    model_card.md

Run:
    python ml/training/train_model.py
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ml.features.build_features import FEATURE_COLUMNS  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
ARTIFACTS_DIR = ROOT / "ml" / "artifacts"


def time_split(df: pd.DataFrame):
    df = df.sort_values("step").reset_index(drop=True)
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def pick_threshold(y_true: np.ndarray, y_score: np.ndarray, min_recall: float = 0.85) -> dict:
    """Pick the lowest threshold that still hits `min_recall` on fraud, to keep
    recall high (missed fraud is expensive) while reporting the precision cost.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    # precision/recall have one more element than thresholds; align.
    candidates = [
        (t, p, r) for t, p, r in zip(thresholds, precision[:-1], recall[:-1]) if r >= min_recall
    ]
    if not candidates:
        chosen = (thresholds[len(thresholds) // 2], precision[len(thresholds) // 2], recall[len(thresholds) // 2])
    else:
        chosen = max(candidates, key=lambda c: c[0])  # highest threshold that still clears min_recall
    return {"threshold": float(chosen[0]), "precision_at_threshold": float(chosen[1]), "recall_at_threshold": float(chosen[2])}


def evaluate(y_true, y_score, threshold) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "precision": float(tp / (tp + fp)) if (tp + fp) else 0.0,
        "recall": float(tp / (tp + fn)) if (tp + fn) else 0.0,
    }


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(PROCESSED_DIR / "features.parquet")
    print(f"Loaded {len(df):,} rows, fraud rate {df['is_fraud'].mean():.3%}")

    train, val, test = time_split(df)
    print(f"train={len(train):,} val={len(val):,} test={len(test):,}")

    X_train, y_train = train[FEATURE_COLUMNS], train["is_fraud"]
    X_val, y_val = val[FEATURE_COLUMNS], val["is_fraud"]
    X_test, y_test = test[FEATURE_COLUMNS], test["is_fraud"]

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        early_stopping_rounds=30,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    val_scores = model.predict_proba(X_val)[:, 1]
    threshold_info = pick_threshold(y_val.to_numpy(), val_scores, min_recall=0.85)
    print(f"Chosen threshold: {threshold_info}")

    test_scores = model.predict_proba(X_test)[:, 1]
    test_metrics = evaluate(y_test.to_numpy(), test_scores, threshold_info["threshold"])
    print(f"Test metrics: {json.dumps(test_metrics, indent=2)}")

    # Unsupervised companion signal: trained on the training split only, unlabeled.
    anomaly_model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1)
    anomaly_model.fit(X_train)
    # Higher = more anomalous, rescaled to roughly [0, 1] for readability alongside risk_score.
    raw_anomaly = -anomaly_model.score_samples(X_test)
    anomaly_auc = roc_auc_score(y_test, raw_anomaly)
    print(f"IsolationForest alone ROC-AUC on test: {anomaly_auc:.4f} (reported for context; not used to threshold)")

    joblib.dump(model, ARTIFACTS_DIR / "model.joblib")
    joblib.dump(anomaly_model, ARTIFACTS_DIR / "anomaly_model.joblib")
    (ARTIFACTS_DIR / "feature_columns.json").write_text(json.dumps(FEATURE_COLUMNS, indent=2))
    (ARTIFACTS_DIR / "threshold.json").write_text(json.dumps(threshold_info, indent=2))

    importances = sorted(
        zip(FEATURE_COLUMNS, model.feature_importances_.tolist()), key=lambda x: -x[1]
    )
    metrics = {
        "test": test_metrics,
        "threshold_selection": threshold_info,
        "isolation_forest_roc_auc_test": float(anomaly_auc),
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "train_fraud_rate": float(y_train.mean()),
        "test_fraud_rate": float(y_test.mean()),
        "top_features": importances[:10],
    }
    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    model_card = f"""# Model Card — Base Fraud Classifier

- **Algorithm**: XGBoost (`n_estimators=400`, `max_depth=5`), time-ordered train/val/test split
  (70/15/15 by simulation `step`) to avoid leaking future transactions into training.
- **Companion signal**: IsolationForest (unsupervised), reported for context — not used to set
  the operating threshold. ROC-AUC alone on test: {anomaly_auc:.4f}.
- **Features**: transaction-level + causal customer-history aggregates only (see
  `feature_columns.json`). Deliberately excludes geo/IP/device/graph/merchant-reputation
  enrichment — those are reserved for the Investigation Agent's tools post-flagging.
- **Operating threshold**: {threshold_info['threshold']:.4f}, chosen as the highest threshold on
  the validation set that still clears {0.85:.0%} recall (missing fraud is costlier than a false
  positive here — false positives get reviewed by the Investigation Agent + human, not
  auto-declined).
- **Test performance**: PR-AUC {test_metrics['pr_auc']:.4f}, ROC-AUC {test_metrics['roc_auc']:.4f},
  precision {test_metrics['precision']:.3f}, recall {test_metrics['recall']:.3f} at the chosen
  threshold. Confusion matrix: {test_metrics['confusion_matrix']}.
- **Top features by importance**: {', '.join(f"{f} ({v:.3f})" for f, v in importances[:5])}.
- **Known limitations**: trained on a downsampled PaySim (5.2% fraud rate vs PaySim's native
  0.13%), so absolute precision numbers won't transfer to production traffic without
  recalibration; balance-consistency features are strong in PaySim specifically because its
  simulator doesn't perfectly conserve balances on fraudulent transfers, which may not hold on
  real payment rails.
"""
    (ARTIFACTS_DIR / "model_card.md").write_text(model_card)
    print(f"\nArtifacts written to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
