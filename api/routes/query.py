# api/routes/query.py
import json
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

query_bp = Blueprint("query", __name__)


def fetch_rag_context(question: str) -> str:
    context_parts = []

    if os.getenv("AZURE_SUBSCRIPTION_ID"):
        try:
            import mlflow
            from azure.ai.ml import MLClient
            from azure.identity import DefaultAzureCredential

            ml_client = MLClient(
                credential=DefaultAzureCredential(),
                subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
                resource_group_name=os.getenv(
                    "AZURE_RESOURCE_GROUP", "rg-intellipipeline"
                ),
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
            if experiments:
                runs = mlflow.search_runs(
                    experiment_ids=[experiments[0].experiment_id],
                    order_by=["start_time DESC"],
                    max_results=5,
                )
                model_history = []
                for _, run in runs.iterrows():
                    model_history.append(
                        {
                            "run_id": run["run_id"][:8],
                            "timestamp": str(run.get("start_time", "")),
                            "accuracy": run.get("metrics.accuracy"),
                            "fpr": run.get("metrics.false_positive_rate"),
                            "f1": run.get("metrics.f1_score"),
                            "energy_kwh": run.get("metrics.energy_kwh"),
                        }
                    )
                context_parts.append(
                    f"RECENT MODEL RUNS:\n{json.dumps(model_history, indent=2, default=str)}"
                )
        except Exception as e:
            context_parts.append(f"Model history unavailable: {e}")

    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn:
        try:
            from azure.storage.blob import BlobServiceClient

            blob_client = BlobServiceClient.from_connection_string(conn)
            container = blob_client.get_container_client("drift-signals")
            blobs = sorted(
                list(container.list_blobs()),
                key=lambda x: x.last_modified,
                reverse=True,
            )
            if blobs:
                latest_drift = json.loads(
                    container.download_blob(blobs[0].name).readall()
                )
                context_parts.append(
                    f"LATEST DRIFT REPORT:\n{json.dumps(latest_drift, indent=2)}"
                )

            xai_container = blob_client.get_container_client("xai-reports")
            xai_blobs = sorted(
                list(xai_container.list_blobs()),
                key=lambda x: x.last_modified,
                reverse=True,
            )
            if xai_blobs:
                xai_report = json.loads(
                    xai_container.download_blob(xai_blobs[0].name).readall()
                )
                context_parts.append(
                    f"LATEST XAI REPORT:\n{json.dumps(xai_report, indent=2)}"
                )
        except Exception as e:
            context_parts.append(f"Blob context unavailable: {e}")

    data_dir = Path(__file__).resolve().parents[2] / "data"
    xai_path = data_dir / "xai_report.json"
    if xai_path.exists():
        with open(xai_path, encoding="utf-8") as f:
            context_parts.append(f"LOCAL XAI REPORT:\n{f.read()}")

    if not context_parts:
        context_parts.append(
            json.dumps(
                {
                    "platform": "IntelliPipeline",
                    "demo_mode": True,
                    "model_accuracy": 0.924,
                    "false_positive_rate": 0.051,
                    "psi_score": 0.12,
                    "drift_detected": False,
                    "top_features": [
                        "amount_deviation_ratio",
                        "is_new_merchant",
                        "tx_count_7d",
                    ],
                    "question_hint": question,
                },
                indent=2,
            )
        )

    return "\n\n---\n\n".join(context_parts)


@query_bp.route("/api/query", methods=["POST"])
def natural_language_query():
    data = request.get_json() or {}
    question = data.get("question", "")
    conversation_history = data.get("conversation_history", [])

    if not question:
        return jsonify({"error": "Question required"}), 400

    context = fetch_rag_context(question)
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return jsonify(
            {
                "answer": (
                    f"[Demo mode — set ANTHROPIC_API_KEY for live Claude responses]\n\n"
                    f"Based on IntelliPipeline context: current model accuracy is ~92.4%, "
                    f"FPR ~5.1%, PSI drift score ~0.12 (LOW severity, no retraining needed). "
                    f"Top fraud drivers: amount deviation, new merchant, transaction velocity.\n\n"
                    f"Your question: {question}"
                ),
                "context_sources": ["Demo Dataset", "Local XAI"],
                "timestamp": datetime.utcnow().isoformat(),
                "tokens_used": 0,
                "demo_mode": True,
            }
        )

    import anthropic

    claude = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are IntelliPipeline's AI Operations assistant.
You help data scientists, MLOps engineers, and business stakeholders understand
the fraud detection ML platform's current state, performance, and decisions.

Always ground your answers in the provided context data.
Be concise, accurate, and honest about what you don't know."""

    messages = conversation_history + [
        {
            "role": "user",
            "content": f"Context from IntelliPipeline:\n\n{context}\n\n---\n\nQuestion: {question}",
        }
    ]

    response = claude.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )

    answer = response.content[0].text

    return jsonify(
        {
            "answer": answer,
            "context_sources": ["Azure ML MLflow", "Drift Monitor", "XAI Report"],
            "timestamp": datetime.utcnow().isoformat(),
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        }
    )
