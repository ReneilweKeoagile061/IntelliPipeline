"""
Layer 2 (local): Feature validation without Great Expectations (stdlib checks).
Run: python feature_store/local/validate_features.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from local_paths import BASELINES_DIR, FEATURES_CSV, resolve_features_path  # noqa: E402

REQUIRED = [
    "customer_id",
    "transaction_amount",
    "is_fraud",
    "rule_based_risk",
]


def main():
    path = resolve_features_path()
    if not path.exists():
        raise FileNotFoundError(f"Features not found: {path}")

    df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)
    failures = []

    for col in REQUIRED:
        if col not in df.columns:
            failures.append(f"Missing column: {col}")

    if "transaction_amount" in df.columns:
        if (df["transaction_amount"] <= 0).any():
            failures.append("transaction_amount must be positive")
        if df["transaction_amount"].max() > 1_000_000:
            failures.append("transaction_amount exceeds max")

    if "rule_based_risk" in df.columns:
        if df["rule_based_risk"].min() < 0 or df["rule_based_risk"].max() > 1:
            failures.append("rule_based_risk out of [0,1]")

    if "is_fraud" in df.columns:
        rate = df["is_fraud"].mean()
        if rate < 0.005 or rate > 0.05:
            failures.append(f"is_fraud rate {rate:.3f} outside [0.5%, 5%]")

    for col in ["customer_id", "transaction_amount", "is_fraud"]:
        if col in df.columns and df[col].isna().any():
            failures.append(f"Nulls in {col}")

    baseline_path = BASELINES_DIR / "amount_distribution.json"
    mean_amt = float(df["transaction_amount"].mean())
    std_amt = float(df["transaction_amount"].std())
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        shift = abs(mean_amt - baseline["mean"]) / baseline["mean"]
        if shift > 0.15:
            print(f"WARNING: amount distribution shift {shift:.1%}")
    else:
        baseline_path.write_text(
            json.dumps({"mean": mean_amt, "std": std_amt}), encoding="utf-8"
        )
        print(f"Saved baseline -> {baseline_path}")

    if failures:
        for f in failures:
            print(f"FAILED: {f}")
        raise SystemExit(f"{len(failures)} validation checks failed")

    print(f"All validation checks passed ({len(df):,} rows).")


if __name__ == "__main__":
    main()
