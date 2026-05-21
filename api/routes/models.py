# api/routes/models.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, jsonify

models_bp = Blueprint("models", __name__)


def _demo_model_health():
    return {
        "model_name": "intellipipeline-fraud-model",
        "version": "latest",
        "accuracy": 0.924,
        "false_positive_rate": 0.051,
        "f1_score": 0.89,
        "roc_auc": 0.96,
        "endpoint_status": "healthy",
        "traffic_split": {"blue": 90, "green": 10},
        "last_trained": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "predictions_24h": 12847,
    }


@models_bp.route("/api/models/health", methods=["GET"])
def model_health():
    local_metrics = (
        Path(__file__).resolve().parents[2] / "data" / "local" / "model_metrics.json"
    )
    if local_metrics.exists():
        import json

        m = json.loads(local_metrics.read_text(encoding="utf-8"))
        return jsonify(
            {
                **_demo_model_health(),
                "accuracy": m.get("accuracy", 0.924),
                "false_positive_rate": m.get("false_positive_rate", 0.051),
                "f1_score": m.get("f1_score", 0.89),
                "run_id": m.get("run_id"),
                "mode": "local",
            }
        )

    if not os.getenv("AZURE_SUBSCRIPTION_ID"):
        return jsonify(_demo_model_health())

    try:
        import mlflow
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential

        ml_client = MLClient(
            credential=DefaultAzureCredential(),
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
            resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
            workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
        )
        mlflow.set_tracking_uri(
            ml_client.workspaces.get(
                os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline")
            ).mlflow_tracking_uri
        )

        experiments = mlflow.search_experiments(
            filter_string="name = 'intellipipeline-fraud-detection'"
        )
        if not experiments:
            return jsonify(_demo_model_health())

        runs = mlflow.search_runs(
            experiment_ids=[experiments[0].experiment_id],
            order_by=["start_time DESC"],
            max_results=1,
        )
        if runs.empty:
            return jsonify(_demo_model_health())

        run = runs.iloc[0]
        return jsonify(
            {
                "model_name": "intellipipeline-fraud-model",
                "run_id": run["run_id"][:8],
                "accuracy": float(run.get("metrics.accuracy", 0.924) or 0.924),
                "false_positive_rate": float(
                    run.get("metrics.false_positive_rate", 0.051) or 0.051
                ),
                "f1_score": float(run.get("metrics.f1_score", 0.89) or 0.89),
                "roc_auc": float(run.get("metrics.roc_auc", 0.96) or 0.96),
                "endpoint_status": "healthy",
                "last_trained": str(run.get("start_time", "")),
            }
        )
    except Exception as e:
        return jsonify({**_demo_model_health(), "warning": str(e)})


@models_bp.route("/api/green-metrics", methods=["GET"])
def green_metrics():
    time_range = "7d"
    from flask import request

    time_range = request.args.get("range", "7d")

    if not os.getenv("AZURE_SUBSCRIPTION_ID"):
        return jsonify(
            {
                "range": time_range,
                "total_energy_kwh": 12.4,
                "total_co2_grams": 5890,
                "training_runs": 8,
                "efficiency_records_per_kwh": 45200,
                "daily": [
                    {"date": "Mon", "kwh": 1.8, "co2": 855},
                    {"date": "Tue", "kwh": 2.1, "co2": 998},
                    {"date": "Wed", "kwh": 1.5, "co2": 712},
                    {"date": "Thu", "kwh": 2.4, "co2": 1140},
                    {"date": "Fri", "kwh": 1.9, "co2": 903},
                    {"date": "Sat", "kwh": 1.2, "co2": 570},
                    {"date": "Sun", "kwh": 1.5, "co2": 712},
                ],
            }
        )

    try:
        import mlflow
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential

        ml_client = MLClient(
            credential=DefaultAzureCredential(),
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
            resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
            workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
        )
        mlflow.set_tracking_uri(
            ml_client.workspaces.get(
                os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline")
            ).mlflow_tracking_uri
        )
        experiments = mlflow.search_experiments(
            filter_string="name LIKE 'intellipipeline%'"
        )
        if not experiments:
            return jsonify({"range": time_range, "total_energy_kwh": 0})

        runs = mlflow.search_runs(
            experiment_ids=[e.experiment_id for e in experiments],
            order_by=["start_time DESC"],
            max_results=20,
        )
        energy_col = runs.get("metrics.energy_kwh")
        co2_col = runs.get("metrics.co2_grams")
        energy = float(energy_col.fillna(0).sum()) if energy_col is not None else 0.0
        co2 = float(co2_col.fillna(0).sum()) if co2_col is not None else 0.0
        return jsonify(
            {
                "range": time_range,
                "total_energy_kwh": float(energy),
                "total_co2_grams": float(co2),
                "training_runs": len(runs),
            }
        )
    except Exception:
        return jsonify(
            {
                "range": time_range,
                "total_energy_kwh": 12.4,
                "total_co2_grams": 5890,
                "training_runs": 8,
                "demo_fallback": True,
            }
        )
