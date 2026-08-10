"""
Scoring interface used by the rest of the pipeline (the batch runner, the
API) to turn a raw transaction row into risk_score / anomaly_score without
each caller needing to know about feature engineering or artifact paths.

    from ml.scoring import FraudScorer
    scorer = FraudScorer()
    result = scorer.score_transaction(transaction_row_dict)
    # -> {"risk_score": 0.87, "anomaly_score": 0.41, "above_threshold": True, "threshold": 0.52}
"""
import json
from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd

from ml.features.build_features import FEATURE_COLUMNS, build_features

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


class FraudScorer:
    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR):
        self.model = joblib.load(artifacts_dir / "model.joblib")
        self.anomaly_model = joblib.load(artifacts_dir / "anomaly_model.joblib")
        self.feature_columns = json.loads((artifacts_dir / "feature_columns.json").read_text())
        self.threshold = json.loads((artifacts_dir / "threshold.json").read_text())["threshold"]
        self.model_version = "xgb-v1"

    def score_dataframe(self, tx: pd.DataFrame) -> pd.DataFrame:
        """tx must have the same raw columns as data/processed/transactions.parquet."""
        featured = build_features(tx)
        X = featured[self.feature_columns]
        risk_scores = self.model.predict_proba(X)[:, 1]
        # rescale IsolationForest's unbounded score_samples output to ~[0,1] via a logistic
        # squash around 0 so it reads comparably alongside risk_score.
        raw_anomaly = -self.anomaly_model.score_samples(X)
        anomaly_scores = 1 / (1 + pd.Series(raw_anomaly).apply(lambda v: 2.718281828 ** (-8 * (v - 0.5))))

        out = featured[["transaction_id"]].copy()
        out["risk_score"] = risk_scores
        out["anomaly_score"] = anomaly_scores.to_numpy()
        out["above_threshold"] = out["risk_score"] >= self.threshold
        out["model_version"] = self.model_version
        return out

    def score_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        df = pd.DataFrame([transaction])
        scored = self.score_dataframe(df).iloc[0]
        return {
            "transaction_id": scored["transaction_id"],
            "risk_score": float(scored["risk_score"]),
            "anomaly_score": float(scored["anomaly_score"]),
            "above_threshold": bool(scored["above_threshold"]),
            "threshold": self.threshold,
            "model_version": self.model_version,
        }
