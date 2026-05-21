# ml_training/automl_benchmark.py
"""Benchmark RandomForest against simpler baselines."""

import os

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

FEATURE_PATH = os.getenv(
    "FEATURE_STORE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "fraud_features.parquet"),
)
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

df = pd.read_parquet(os.path.normpath(FEATURE_PATH))
X = StandardScaler().fit_transform(df[FEATURE_COLS])
y = df["is_fraud"]

models = {
    "LogisticRegression": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "GradientBoosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
    "RandomForest": RandomForestClassifier(
        n_estimators=200, max_depth=15, class_weight="balanced", random_state=42
    ),
}

print("AutoML Benchmark (5-fold CV)")
print("-" * 50)
for name, model in models.items():
    acc = cross_val_score(model, X, y, cv=5, scoring="accuracy").mean()
    f1 = cross_val_score(model, X, y, cv=5, scoring="f1").mean()
    print(f"{name:22s} accuracy={acc:.4f}  f1={f1:.4f}")
