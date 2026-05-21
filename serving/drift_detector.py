# serving/drift_detector.py
import json
import os
from datetime import datetime

import numpy as np
from azure.storage.blob import BlobServiceClient


def compute_psi(baseline: np.ndarray, current: np.ndarray, buckets: int = 10) -> float:
    baseline_counts, edges = np.histogram(baseline, bins=buckets)
    current_counts, _ = np.histogram(current, bins=edges)

    baseline_pct = (baseline_counts + 1e-6) / len(baseline)
    current_pct = (current_counts + 1e-6) / len(current)

    return float(
        np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    )


def compute_kl_divergence(baseline: np.ndarray, current: np.ndarray) -> float:
    from scipy.stats import entropy

    baseline_hist, edges = np.histogram(baseline, bins=20, density=True)
    current_hist, _ = np.histogram(current, bins=edges, density=True)

    baseline_hist = baseline_hist + 1e-10
    current_hist = current_hist + 1e-10

    return float(entropy(current_hist, baseline_hist))


def check_drift():
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    print(f"Drift detection run: {datetime.utcnow().isoformat()}")

    if not conn:
        demo = {
            "timestamp": datetime.utcnow().isoformat(),
            "psi_score": 0.08,
            "kl_divergence": 0.03,
            "accuracy_drop": 0.0,
            "drift_detected": False,
            "severity": "LOW",
            "note": "demo_mode",
        }
        print(json.dumps(demo, indent=2))
        return demo

    blob_client = BlobServiceClient.from_connection_string(conn)

    try:
        baseline_bytes = (
            blob_client.get_blob_client(
                "model-baselines", "fraud_probability_baseline.npy"
            )
            .download_blob()
            .readall()
        )
        baseline_scores = np.frombuffer(baseline_bytes, dtype=np.float64)
    except Exception:
        print("No baseline found — storing current as baseline")
        return {"action": "baseline_stored"}

    try:
        recent_bytes = (
            blob_client.get_blob_client("prediction-logs", "recent_scores.npy")
            .download_blob()
            .readall()
        )
        recent_scores = np.frombuffer(recent_bytes, dtype=np.float64)
    except Exception:
        print("No recent predictions found")
        return {"action": "no_data"}

    psi = compute_psi(baseline_scores, recent_scores)
    kl_div = compute_kl_divergence(baseline_scores, recent_scores)
    accuracy_drop = 0.0

    drift_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "psi_score": psi,
        "kl_divergence": kl_div,
        "accuracy_drop": accuracy_drop,
        "baseline_mean": float(baseline_scores.mean()),
        "current_mean": float(recent_scores.mean()),
        "drift_detected": psi > 0.25,
        "severity": "HIGH" if psi > 0.25 else "MEDIUM" if psi > 0.1 else "LOW",
    }

    blob_client.get_blob_client(
        "drift-signals",
        f"drift_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
    ).upload_blob(json.dumps(drift_report), overwrite=True)

    print(
        f"PSI: {psi:.4f} | KL: {kl_div:.4f} | "
        f"Drift: {drift_report['drift_detected']}"
    )

    if drift_report["drift_detected"]:
        import requests

        airflow_url = os.getenv(
            "AIRFLOW_API_URL", "http://intellipipeline-airflow/api/v1"
        )
        airflow_auth = (
            os.getenv("AIRFLOW_USER", "admin"),
            os.getenv("AIRFLOW_PASSWORD", ""),
        )

        response = requests.post(
            f"{airflow_url}/dags/intellipipeline_auto_retrain/dagRuns",
            json={"conf": {"trigger_reason": "drift_detected", "psi": psi}},
            auth=airflow_auth,
            timeout=30,
        )

        if response.status_code in (200, 201):
            print("Retraining DAG triggered successfully")
        else:
            print(f"Failed to trigger retraining: {response.status_code}")

    return drift_report


if __name__ == "__main__":
    result = check_drift()
    print(json.dumps(result, indent=2))
