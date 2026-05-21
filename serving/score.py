# serving/score.py — Azure ML managed endpoint scoring script
import json
import os
import pickle

import numpy as np

rf_model = None
scaler = None


def init():
    """Called once when endpoint starts."""
    global rf_model, scaler

    model_dir = os.getenv("AZUREML_MODEL_DIR", ".")

    import mlflow.sklearn

    rf_model = mlflow.sklearn.load_model(os.path.join(model_dir, "rf_fraud_model"))

    scaler_path = os.path.join(model_dir, "scaler.pkl")
    if os.path.exists(scaler_path):
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
    else:
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()

    print("IntelliPipeline scoring script initialised")


def run(raw_data):
    """Called on every prediction request."""
    data = json.loads(raw_data)

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

    if isinstance(data.get("instances"), list):
        records = data["instances"]
    else:
        records = [data]

    results = []
    for record in records:
        features = np.array([[record.get(f, 0) for f in FEATURE_ORDER]])
        features_scaled = scaler.transform(features)

        prediction = int(rf_model.predict(features_scaled)[0])
        probability = float(rf_model.predict_proba(features_scaled)[0][1])

        results.append(
            {
                "prediction": prediction,
                "fraud_probability": round(probability, 4),
                "risk_level": (
                    "HIGH"
                    if probability > 0.7
                    else "MEDIUM"
                    if probability > 0.3
                    else "LOW"
                ),
                "model_version": os.getenv("MODEL_VERSION", "latest"),
            }
        )

    return json.dumps(results if len(results) > 1 else results[0])
