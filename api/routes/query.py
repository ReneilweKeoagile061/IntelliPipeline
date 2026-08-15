# api/routes/query.py
import json
import os
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from google.genai.errors import ServerError, ClientError

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

    # Two possible layouts: full repo checkout (local dev) vs. the
    # api/-only Vercel deployment, which ships its own data/ copy.
    data_dir_candidates = [
        Path(__file__).resolve().parents[2] / "data",  # repo-root/data
        Path(__file__).resolve().parents[1] / "data",  # api/data
    ]

    def _first_existing(relative_path: str):
        for base in data_dir_candidates:
            candidate = base / relative_path
            if candidate.exists():
                return candidate
        return None

    metrics_path = _first_existing("local/model_metrics.json")
    if metrics_path:
        with open(metrics_path, encoding="utf-8") as f:
            context_parts.append(f"LOCAL MODEL METRICS:\n{f.read()}")

    drift_path = _first_existing("local/drift_signals/latest_drift.json")
    if drift_path:
        with open(drift_path, encoding="utf-8") as f:
            context_parts.append(f"LOCAL DRIFT REPORT:\n{f.read()}")

    xai_path = _first_existing("xai_report.json")
    if xai_path:
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


def _extract_json_block(context: str, label: str):
    """Pull a JSON object out of a labeled section of the RAG context, if present."""
    marker = f"{label}:\n"
    idx = context.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    end = context.find("\n\n---\n\n", start)
    block = context[start:end] if end != -1 else context[start:]
    try:
        return json.loads(block)
    except (json.JSONDecodeError, ValueError):
        return None


def _intelligent_fallback_answer(question: str, context: str = "") -> str:
    """Enhanced fallback that provides contextual answers based on question keywords.
    Where real local data is available in `context`, it's used in place of
    hardcoded placeholder numbers.

    NOTE ON ORDERING: patterns are checked most-specific-first. Drift is
    checked before Performance because a question like "current model drift
    status" contains both "model" and "drift" — if Performance were checked
    first with a generic 'model' keyword, it would wrongly win. Keep new
    patterns' keyword lists as specific as possible, and place broader
    patterns later in this chain.
    """

    question_lower = question.lower()

    # Pattern 1: Fraud patterns / features / SHAP
    if any(word in question_lower for word in ['fraud pattern', 'top feature', 'shap', 'important feature', 'driver']):
        real_xai = _extract_json_block(context, "LOCAL XAI REPORT")
        if real_xai and real_xai.get("top_features"):
            lines = "\n".join(
                f"{i+1}. **{name}** (importance: {score:.4f})"
                for i, (name, score) in enumerate(real_xai["top_features"])
            )
            return f"""Based on SHAP analysis from the latest local run (Run ID: `{real_xai.get('run_id', 'unknown')}`), the top fraud indicators are:

{lines}

Explanation stability: {real_xai.get('explanation_stability', 'N/A')}
Interpretable population: {real_xai.get('interpretable_for_pct', 'N/A')}"""
        return """Based on SHAP analysis from the current model, the top fraud patterns are:

1. **Amount Deviation** (SHAP: 0.42) — Transactions 3-5x higher than customer's 30-day average indicate possible account takeover. This appears in 68% of confirmed fraud cases.

2. **New Merchant Activity** (SHAP: 0.31) — First-time transactions at unfamiliar merchants combined with unusual amounts. Detected in 47% of card-not-present fraud.

3. **Transaction Velocity** (SHAP: 0.18) — Spike to 10+ transactions in 24 hours vs. baseline of 2-3 per day. Common in card testing attacks (23% of cases).

4. **Time-of-Day Anomalies** (SHAP: 0.11) — Transactions during hours inconsistent with customer history (e.g., 3 AM purchases for daytime-only customers).

Current model achieves 98.99% accuracy with 0.45% false positive rate."""

    # Pattern 2: Drift detection (checked before Performance — see note above)
    elif any(word in question_lower for word in ['drift', 'psi', 'data quality', 'distribution']):
        real_drift = _extract_json_block(context, "LOCAL DRIFT REPORT")
        if real_drift:
            status = "✅ Model performance stable" if not real_drift.get("drift_detected") else "⚠️ Drift detected"
            return f"""Drift Detection Status (from latest local run, {real_drift.get('timestamp', 'unknown time')}):

**PSI Score:** {real_drift.get('psi_score', 'N/A')}
**KL Divergence:** {real_drift.get('kl_divergence', 'N/A')}
**Severity:** {real_drift.get('severity', 'N/A')}
**Status:** {status}
**Accuracy Drop:** {real_drift.get('accuracy_drop', 'N/A')}
**Auto-Retrain Triggered:** {real_drift.get('should_retrain', 'N/A')}

**Thresholds:**
- PSI < 0.1: No action needed
- PSI 0.1-0.25: Monitor closely
- PSI > 0.25: Retrain recommended

Drift monitoring runs daily at 2:00 AM UTC. Auto-retraining triggers when PSI > 0.25 for 3 consecutive days."""
        return """Drift Detection Status:

No local drift report is currently available. Run the local pipeline (`python scripts/run_local_pipeline.py`) to generate one.

**Thresholds:**
- PSI < 0.1: No action needed
- PSI 0.1-0.25: Monitor closely
- PSI > 0.25: Retrain recommended

Drift monitoring runs daily at 2:00 AM UTC. Auto-retraining triggers when PSI > 0.25 for 3 consecutive days."""

    # Pattern 3: Model performance / metrics
    elif any(word in question_lower for word in ['performance', 'accuracy', 'metric', 'confusion matrix']):
        real_metrics = _extract_json_block(context, "LOCAL MODEL METRICS")
        if real_metrics:
            return f"""Model Performance Metrics (from latest local run):

{json.dumps(real_metrics, indent=2)}

These figures come directly from the most recent local training run, not a fixed demo value."""
        return """Model Performance Metrics (Current Production Model):

**Classification Metrics:**
- Accuracy: 98.99%
- Precision: 3.23%
- Recall: 2.61%
- F1 Score: 0.0288
- ROC AUC: 0.7455
- False Positive Rate: 0.45%

**Confusion Matrix (Test Set, n=20,000):**
- True Negatives: 19,795 (correctly identified legitimate transactions)
- False Positives: 90 (legitimate flagged as fraud)
- False Negatives: 112 (missed fraud cases)
- True Positives: 3 (correctly caught fraud)

**Optimization Target:** Minimizing false positives while maintaining fraud detection capability. Current 0.45% FPR represents 96% improvement over baseline rule-based system (12% FPR)."""

    # Pattern 4: Energy / Green metrics
    elif any(word in question_lower for word in ['energy', 'green', 'carbon', 'co2', 'kwh']):
        return """Green MLOps Metrics (Last 7 Days):

**Energy Consumption:**
- Model Training: 8.4 kWh (Random Forest, 200 estimators, 3 CV folds)
- Feature Engineering: 2.1 kWh (Delta Lake aggregations, 100K transactions)
- Inference (100K predictions): 1.9 kWh
- **Total:** 12.4 kWh

**Carbon Footprint:**
- CO₂ Equivalent: 5.2 kg (assuming 0.42 kg CO₂/kWh grid mix)
- Equivalent to: ~12 miles driven in average car

**Efficiency Metrics:**
- Energy per prediction: 0.019 Wh
- Energy per training epoch: 2.8 kWh
- Delta Lake optimization: Saves ~30% vs. Parquet reprocessing

**ESG Compliance:** Tracking enabled for Scope 2 emissions reporting (electricity consumption from ML operations).

Note: no local energy-tracking data is currently wired into this pipeline — these are illustrative figures, not measured values."""

    # Pattern 5: Retraining / pipeline automation
    elif any(word in question_lower for word in ['retrain', 'pipeline', 'automation', 'trigger']):
        return """Auto-Retraining Pipeline Configuration:

**Trigger Conditions (Any of):**
1. PSI > 0.25 for 3 consecutive days
2. Model accuracy drops below 95% on validation set
3. False positive rate exceeds 1.0%
4. Manual trigger via MLflow UI

**Pipeline Steps:**
1. **Data Refresh** — Pull latest 90 days from Delta Lake feature store
2. **Feature Engineering** — Recalculate aggregates (tx_count_7d, avg_amount_30d, etc.)
3. **Training** — Random Forest with 3-fold CV, balanced class weights
4. **Validation** — Test on holdout set (20%), check FPR < 1%
5. **SHAP Calculation** — Generate explainability artifacts
6. **MLflow Logging** — Version model, metrics, SHAP values
7. **Deployment** — Blue-green swap if validation passes

**Estimated Runtime:** 18-25 minutes (depends on data volume)
**Rollback Policy:** Auto-rollback if new model FPR > 1.5x old model FPR"""

    # Pattern 6: Explainability / SHAP / XAI
    elif any(word in question_lower for word in ['explain', 'shap', 'xai', 'interpretability']):
        real_xai = _extract_json_block(context, "LOCAL XAI REPORT")
        stability_line = (
            f"\n\n**From your latest local run:** explanation stability {real_xai.get('explanation_stability', 'N/A')}, "
            f"interpretable for {real_xai.get('interpretable_for_pct', 'N/A')} of predictions."
            if real_xai else ""
        )
        return f"""XAI (Explainable AI) Approach:

**Method:** SHAP (SHapley Additive exPlanations)
- Calculates each feature's contribution to every prediction
- Based on game theory (Shapley values from cooperative game theory)
- Model-agnostic, works with any ML algorithm

**Why SHAP for Banking:**
1. **Regulatory Compliance** — Meets GDPR Article 22 (right to explanation), SR 11-7 (model risk management)
2. **Audit Trail** — Every fraud decision is explainable and logged
3. **Trust** — Analysts can verify model logic matches domain expertise

**Example Output:**
Transaction TX-2025-88421 flagged as fraud (87% confidence)
- amount_deviation_ratio: +0.42 (amount 4.2x higher than usual)
- is_new_merchant: +0.31 (first time at this merchant)
- tx_count_7d: +0.18 (10 transactions vs. normal 3)

**Performance:** SHAP calculation adds ~15ms per prediction (negligible for fraud detection use case).{stability_line}"""

    # Generic fallback for unmatched queries
    else:
        return f"""[Demo mode — set GEMINI_API_KEY for AI-powered query understanding]

Based on IntelliPipeline MLflow context:
- Current model: Random Forest (200 estimators, max_depth=15)
- Accuracy: 98.99% | FPR: 0.45% | ROC AUC: 0.7455
- Feature store: Unity Catalog Delta Lake table
- Drift monitoring: PSI-based with auto-retrain triggers
- Explainability: Real-time SHAP analysis

Try asking:
- "What are the top fraud patterns?"
- "Show me model performance metrics"
- "Is there any drift detected?"
- "How much energy did the model use?"
- "When does auto-retraining trigger?"
- "Explain how SHAP works"

Your question: "{question}" """


def _is_retryable(exc: BaseException) -> bool:
    """Retry on server-side overload, and on client-side rate limiting (429)."""
    if isinstance(exc, ServerError):
        return True
    if isinstance(exc, ClientError) and getattr(exc, "code", None) == 429:
        return True
    return False


@query_bp.route("/api/query", methods=["POST"])
def natural_language_query():
    data = request.get_json() or {}
    question = data.get("question", "")
    conversation_history = data.get("conversation_history", [])

    if not question:
        return jsonify({"error": "Question required"}), 400

    context = fetch_rag_context(question)
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        # Use intelligent fallback instead of generic demo message
        return jsonify(
            {
                "answer": _intelligent_fallback_answer(question, context),
                "context_sources": ["Demo Dataset", "Local XAI", "SHAP Analysis"],
                "timestamp": datetime.utcnow().isoformat(),
                "tokens_used": 0,
                "demo_mode": True,
            }
        )

    from google import genai
    from google.genai import types

    gemini = genai.Client(api_key=api_key)

    system_prompt = """You are IntelliPipeline's AI Operations assistant.
You help data scientists, MLOps engineers, and business stakeholders understand
the fraud detection ML platform's current state, performance, and decisions.

Always ground your answers in the provided context data.
Be concise, accurate, and honest about what you don't know."""

    # Gemini uses role "model" instead of "assistant", and expects
    # Content/Part objects rather than plain role/content dicts.
    gemini_history = [
        types.Content(
            role="model" if m.get("role") == "assistant" else m.get("role", "user"),
            parts=[types.Part.from_text(text=m.get("content", ""))],
        )
        for m in conversation_history
    ]

    contents = gemini_history + [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Context from IntelliPipeline:\n\n{context}\n\n---\n\nQuestion: {question}"
                )
            ],
        )
    ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _call_gemini():
        return gemini.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=800,
            ),
        )

    try:
        response = _call_gemini()
    except (ServerError, ClientError):
        # Gemini overloaded or rate-limited, even after retries — fall back gracefully
        return jsonify(
            {
                "answer": _intelligent_fallback_answer(question, context),
                "context_sources": ["Demo Dataset", "Local XAI", "SHAP Analysis"],
                "timestamp": datetime.utcnow().isoformat(),
                "tokens_used": 0,
                "demo_mode": True,
                "note": "Gemini temporarily unavailable — showing offline analysis",
            }
        )

    answer = response.text

    usage = response.usage_metadata
    tokens_used = (
        (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
        if usage
        else 0
    )

    return jsonify(
        {
            "answer": answer,
            "context_sources": ["Azure ML MLflow", "Drift Monitor", "XAI Report"],
            "timestamp": datetime.utcnow().isoformat(),
            "tokens_used": tokens_used,
        }
    )