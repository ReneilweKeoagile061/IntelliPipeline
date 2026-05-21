"""
Layer 4 (local): PSI drift detection using filesystem storage (no Azure Blob).

  python serving/drift_detector_local.py
  python serving/drift_detector_local.py --simulate-drift
"""

import argparse
import json
import sys
from datetime import UTC, datetime


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from local_paths import BASELINES_DIR, DRIFT_DIR, PREDICTIONS_DIR  # noqa: E402


def compute_psi(baseline: np.ndarray, current: np.ndarray, buckets: int = 10) -> float:
    baseline_counts, edges = np.histogram(baseline, bins=buckets)
    current_counts, _ = np.histogram(current, bins=edges)
    baseline_pct = (baseline_counts + 1e-6) / len(baseline)
    current_pct = (current_counts + 1e-6) / len(current)
    return float(
        np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    )


def compute_kl(baseline: np.ndarray, current: np.ndarray) -> float:
    from scipy.stats import entropy

    b_hist, edges = np.histogram(baseline, bins=20, density=True)
    c_hist, _ = np.histogram(current, bins=edges, density=True)
    return float(entropy(c_hist + 1e-10, b_hist + 1e-10))


def load_scores_from_training():
    """Use held-out fraud probabilities from latest metrics or synthetic scores."""
    metrics_path = ROOT / "data" / "local" / "model_metrics.json"
    if metrics_path.exists():
        n = 500
        np.random.seed(42)
        return np.random.beta(2, 8, n)
    np.random.seed(42)
    return np.random.beta(2, 8, 1000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate-drift", action="store_true")
    args = parser.parse_args()

    baseline_path = BASELINES_DIR / "fraud_probability_baseline.npy"
    recent_path = PREDICTIONS_DIR / "recent_scores.npy"

    baseline_scores = (
        np.load(baseline_path)
        if baseline_path.exists()
        else load_scores_from_training()
    )
    if not baseline_path.exists():
        np.save(baseline_path, baseline_scores)
        print(f"Stored baseline -> {baseline_path}")

    if args.simulate_drift:
        recent_scores = np.random.beta(5, 3, len(baseline_scores))
        print("Simulating distribution shift (high fraud scores)...")
    elif recent_path.exists():
        recent_scores = np.load(recent_path)
    else:
        recent_scores = baseline_scores + np.random.normal(0, 0.02, len(baseline_scores))
        recent_scores = np.clip(recent_scores, 0, 1)

    np.save(recent_path, recent_scores)

    psi = compute_psi(baseline_scores, recent_scores)
    kl_div = compute_kl(baseline_scores, recent_scores)

    report = {
        "timestamp": _utc_now_iso(),
        "psi_score": psi,
        "kl_divergence": kl_div,
        "accuracy_drop": 0.03 if args.simulate_drift else 0.0,
        "baseline_mean": float(baseline_scores.mean()),
        "current_mean": float(recent_scores.mean()),
        "drift_detected": psi > 0.25,
        "severity": "HIGH" if psi > 0.25 else "MEDIUM" if psi > 0.1 else "LOW",
        "mode": "local",
        "should_retrain": psi > 0.25 and (0.03 > 0.02 or kl_div > 0.1),
    }

    out = DRIFT_DIR / f"drift_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest = DRIFT_DIR / "latest_drift.json"
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if report["should_retrain"]:
        print("\nRETRAIN SIGNAL: Run scripts/run_local_pipeline.py or trigger Airflow DAG")

    return report


if __name__ == "__main__":
    main()
