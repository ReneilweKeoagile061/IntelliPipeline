"""Generate synthetic fraud detection datasets for local development."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

np.random.seed(42)
N = 10_000

n_fraud = int(N * 0.03)
is_fraud = np.zeros(N, dtype=int)
is_fraud[:n_fraud] = 1
np.random.shuffle(is_fraud)

raw = pd.DataFrame(
    {
        "customer_id": [f"C{i % 500:05d}" for i in range(N)],
        "transaction_id": [f"TX-{i:07d}" for i in range(N)],
        "transaction_timestamp": pd.date_range("2024-01-01", periods=N, freq="5min"),
        "transaction_amount": np.round(
            np.random.lognormal(4, 1.2, N) * (1 + is_fraud * 0.5), 2
        ),
        "merchant_category": np.random.choice(
            ["retail", "grocery", "travel", "electronics", "cash_advance"], N
        ),
        "merchant_id": [f"M{np.random.randint(1, 200):04d}" for _ in range(N)],
        "merchant_country": np.random.choice(["BW", "ZA", "US", "GB"], N, p=[0.6, 0.2, 0.1, 0.1]),
        "customer_country": np.random.choice(["BW", "ZA"], N, p=[0.85, 0.15]),
        "customer_age_days": np.random.randint(30, 3650, N),
        "device_fingerprint": [f"DEV-{np.random.randint(1000, 9999)}" for _ in range(N)],
        "hour_of_day": np.random.randint(0, 24, N),
        "is_fraud": is_fraud,
    }
)

def _save_df(df, name):
    csv_path = DATA_DIR / f"{name}.csv"
    df.to_csv(csv_path, index=False)
    if os.getenv("INTELLIPIPELINE_LOCAL", "1") != "1":
        try:
            df.to_parquet(DATA_DIR / f"{name}.parquet", index=False)
        except Exception:
            pass
    return csv_path


_save_df(raw, "sample_transactions")

# Engineered features (simplified — mirrors Databricks notebook logic)
features = raw.copy()
features["tx_count_7d"] = np.random.poisson(3, N) + is_fraud * 5
features["avg_amount_30d"] = features["transaction_amount"] * np.random.uniform(0.5, 1.2, N)
features["amount_deviation_ratio"] = features["transaction_amount"] / (
    features["avg_amount_30d"] + 0.01
)
features["is_weekend"] = (features["transaction_timestamp"].dt.dayofweek >= 5).astype(int)
features["is_new_merchant"] = ((np.random.rand(N) < 0.1) | (is_fraud == 1)).astype(int)
features["is_cross_border"] = (
    features["merchant_country"] != features["customer_country"]
).astype(int)
features["rule_based_risk"] = np.clip(
    features["amount_deviation_ratio"] * 0.1
    + features["is_new_merchant"] * 0.3
    + features["is_cross_border"] * 0.25
    + (features["tx_count_7d"] > 20).astype(float) * 0.2,
    0,
    1,
)
features["feature_version"] = "v1.0"
features["feature_timestamp"] = pd.Timestamp.utcnow()

feature_cols = [
    "customer_id",
    "transaction_id",
    "transaction_timestamp",
    "transaction_amount",
    "merchant_category",
    "merchant_country",
    "customer_country",
    "device_fingerprint",
    "tx_count_7d",
    "avg_amount_30d",
    "amount_deviation_ratio",
    "hour_of_day",
    "is_weekend",
    "is_new_merchant",
    "is_cross_border",
    "rule_based_risk",
    "is_fraud",
    "feature_version",
    "feature_timestamp",
]

features_path = _save_df(features[feature_cols], "fraud_features")

xai_report = {
    "feature_importance": {
        "amount_deviation_ratio": 0.42,
        "is_new_merchant": 0.31,
        "tx_count_7d": 0.18,
        "is_cross_border": 0.15,
        "rule_based_risk": 0.12,
    },
    "top_features": [
        ["amount_deviation_ratio", 0.42],
        ["is_new_merchant", 0.31],
        ["tx_count_7d", 0.18],
    ],
    "explanation_stability": 0.91,
    "methodology": "SHAP TreeExplainer (demo)",
}

with open(DATA_DIR / "xai_report.json", "w", encoding="utf-8") as f:
    json.dump(xai_report, f, indent=2)

print(f"Generated {N:,} records in {DATA_DIR}")
print(f"  - features: {features_path.name}")
print("  - xai_report.json")
