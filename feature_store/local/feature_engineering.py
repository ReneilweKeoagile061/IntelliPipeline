"""
Layer 2 (local): Pandas feature engineering — mirrors Databricks notebook offline.
Run: python feature_store/local/feature_engineering.py
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from local_paths import (  # noqa: E402
    FEATURES_CSV,
    GREEN_METRICS_JSON,
    RAW_CSV,
    RAW_PARQUET,
    resolve_raw_path,
)


def load_raw() -> pd.DataFrame:
    path = resolve_raw_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Raw data missing at {path}. Run: python scripts/generate_sample_data.py"
        )
    if path.suffix == ".csv":
        df = pd.read_csv(path, parse_dates=["transaction_timestamp"])
    else:
        df = pd.read_parquet(path)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["customer_id", "transaction_timestamp"]).copy()
    df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])

    import numpy as np

    np.random.seed(42)
    df["tx_count_7d"] = np.random.poisson(3, len(df)) + df.get("is_fraud", 0).fillna(0) * 5
    g = df.groupby("customer_id", group_keys=False)

    df["avg_amount_30d"] = g["transaction_amount"].transform(
        lambda s: s.expanding().mean().shift(1).fillna(s.mean())
    )
    df["amount_deviation_ratio"] = df["transaction_amount"] / (df["avg_amount_30d"] + 0.01)
    df["hour_of_day"] = df["transaction_timestamp"].dt.hour
    df["is_weekend"] = (df["transaction_timestamp"].dt.dayofweek >= 5).astype(int)
    df["is_new_merchant"] = (
        g["merchant_id"].transform(lambda s: (s.expanding().count() == 1).astype(int))
    )
    df["is_cross_border"] = (df["merchant_country"] != df["customer_country"]).astype(int)
    df["rule_based_risk"] = (
        df["amount_deviation_ratio"].clip(0, 3) * 0.1
        + df["is_new_merchant"] * 0.3
        + df["is_cross_border"] * 0.25
        + (df["tx_count_7d"] > 20).astype(float) * 0.2
    ).clip(0, 1)
    df["feature_version"] = "v1.0-local"
    df["feature_timestamp"] = pd.Timestamp.utcnow().isoformat()

    cols = [
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
    return df[[c for c in cols if c in df.columns]]


def main():
    t0 = time.time()
    raw = load_raw()
    features = engineer_features(raw)
    features.to_csv(FEATURES_CSV, index=False)

    duration = time.time() - t0
    n = len(features)
    estimated_kwh = (duration / 3600) * 0.095 * 4
    green = {
        "compute_duration_seconds": duration,
        "estimated_energy_kwh": estimated_kwh,
        "estimated_co2_grams": estimated_kwh * 475,
        "records_processed": n,
        "mode": "local",
    }
    GREEN_METRICS_JSON.write_text(json.dumps(green, indent=2), encoding="utf-8")

    print(f"Wrote {n:,} features -> {FEATURES_CSV}")
    print(f"Green metrics -> {GREEN_METRICS_JSON}")
    return features


if __name__ == "__main__":
    main()
