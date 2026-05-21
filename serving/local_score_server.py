"""
Local model scoring API (Layer 4) — loads MLflow sklearn model from mlruns/.

  python serving/local_score_server.py
  POST http://localhost:5001/score  {"transaction_amount": 500, "tx_count_7d": 12, ...}
"""

import json
import os
import pickle
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
ROOT = Path(__file__).resolve().parents[1]

FEATURE_ORDER = [
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

model = None
scaler = None


def load_model():
    global model, scaler
    models_dir = ROOT / "data" / "local" / "models"
    pkl = models_dir / "rf_model.pkl"
    scaler_path = models_dir / "scaler.pkl"

    if pkl.exists():
        import joblib

        model = joblib.load(pkl)
        if scaler_path.exists():
            scaler = joblib.load(scaler_path)
        return

    import mlflow.sklearn

    uri = os.getenv("LOCAL_MODEL_URI")
    if not uri:
        runs = sorted((ROOT / "mlruns").rglob("rf_fraud_model"), key=lambda p: p.stat().st_mtime)
        if runs:
            uri = str(runs[-1].parent.parent)
        else:
            raise FileNotFoundError("No model found. Run ml_training/train.py first.")
    model = mlflow.sklearn.load_model(uri)
    scaler_path = Path(uri) / "scaler.pkl"
    if scaler_path.exists():
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "local-score"})


@app.route("/score", methods=["POST"])
def score():
    import numpy as np

    data = request.get_json() or {}
    records = data.get("instances", [data])

    results = []
    for record in records:
        features = np.array([[record.get(f, 0) for f in FEATURE_ORDER]])
        if scaler is not None:
            features = scaler.transform(features)
        pred = int(model.predict(features)[0])
        prob = float(model.predict_proba(features)[0][1])
        results.append(
            {
                "prediction": pred,
                "fraud_probability": round(prob, 4),
                "risk_level": (
                    "HIGH" if prob > 0.7 else "MEDIUM" if prob > 0.3 else "LOW"
                ),
            }
        )

    return jsonify(results[0] if len(results) == 1 else results)


if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=int(os.getenv("SCORE_PORT", "5001")), debug=True)
