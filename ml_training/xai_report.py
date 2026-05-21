# ml_training/xai_report.py
"""Generate standalone XAI report from a trained MLflow run."""

import argparse
import json
import os

import mlflow
import numpy as np
import pandas as pd
import shap

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", required=True)
parser.add_argument("--feature-path", default="data/fraud_features.parquet")
args = parser.parse_args()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
model = mlflow.sklearn.load_model(f"runs:/{args.run_id}/rf_fraud_model")

FEATURE_COLS = [
    "transaction_amount",
    "tx_count_7d",
    "avg_amount_30d",
    "amount_deviation_ratio",
    "hour_of_day",
    "is_weekend",
    "is_new_merchant",
    "is_cross_border",
    "rule_based_risk",
]

df = pd.read_parquet(args.feature_path)
X = df[FEATURE_COLS].sample(min(500, len(df)), random_state=42)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
shap_class = shap_values[1] if isinstance(shap_values, list) else shap_values

report = {
    "run_id": args.run_id,
    "feature_importance": dict(
        zip(FEATURE_COLS, np.abs(shap_class).mean(axis=0).tolist())
    ),
    "methodology": "SHAP TreeExplainer",
}

with open("xai_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
