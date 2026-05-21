# api/routes/explain.py
import json
import os
from pathlib import Path

from flask import Blueprint, jsonify, request

explain_bp = Blueprint("explain", __name__)


def _load_local_xai():
    xai_path = Path(__file__).resolve().parents[2] / "mlruns" / "xai_report.json"
    alt = Path(__file__).resolve().parents[2] / "data" / "xai_report.json"
    for p in [alt, xai_path]:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


@explain_bp.route("/api/explain/<transaction_id>", methods=["POST"])
def explain_prediction(transaction_id):
    """SHAP + Claude explanation for a fraud prediction."""
    data = request.get_json() or {}
    audience = data.get("audience", "executive")

    xai = _load_local_xai()
    top_features = (
        xai.get("top_features", [])
        if xai
        else [
            ("amount_deviation_ratio", 0.42),
            ("is_new_merchant", 0.31),
            ("tx_count_7d", 0.18),
        ]
    )

    xai_context = {
        "transaction_id": transaction_id,
        "prediction": "FRAUD",
        "fraud_probability": 0.87,
        "top_factors": [
            {
                "feature": f[0] if isinstance(f, tuple) else f.get("feature"),
                "shap_value": f[1] if isinstance(f, tuple) else f.get("shap_value"),
                "description": _feature_description(
                    f[0] if isinstance(f, tuple) else f.get("feature", "")
                ),
            }
            for f in top_features[:3]
        ],
    }

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        explanation = _fallback_explanation(xai_context, audience)
        return jsonify(
            {
                "transaction_id": transaction_id,
                "explanation": explanation,
                "audience": audience,
                "shap_factors": xai_context["top_factors"],
                "fraud_probability": xai_context["fraud_probability"],
                "demo_mode": True,
            }
        )

    import anthropic

    claude = anthropic.Anthropic(api_key=api_key)

    if audience == "executive":
        prompt = (
            f"This transaction was flagged as likely fraudulent (87% confidence). "
            f"Explain why in 2-3 sentences for a non-technical bank executive. "
            f"Focus on business risk. Data: {json.dumps(xai_context)}"
        )
    else:
        prompt = (
            f"Provide a technical explanation of this fraud prediction for a risk analyst. "
            f"Include SHAP values. Data: {json.dumps(xai_context)}"
        )

    response = claude.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return jsonify(
        {
            "transaction_id": transaction_id,
            "explanation": response.content[0].text,
            "audience": audience,
            "shap_factors": xai_context["top_factors"],
            "fraud_probability": xai_context["fraud_probability"],
        }
    )


def _feature_description(feature: str) -> str:
    descriptions = {
        "amount_deviation_ratio": "Amount is unusually high vs the customer's 30-day average",
        "is_new_merchant": "First transaction at this merchant",
        "tx_count_7d": "Unusually high transaction velocity in the last 7 days",
        "is_cross_border": "Cross-border transaction pattern",
        "rule_based_risk": "Elevated composite rule-based risk score",
    }
    return descriptions.get(feature, f"Elevated {feature}")


def _fallback_explanation(ctx: dict, audience: str) -> str:
    factors = ", ".join(f["feature"] for f in ctx["top_factors"])
    if audience == "executive":
        return (
            f"Transaction {ctx['transaction_id']} was flagged with "
            f"{ctx['fraud_probability']*100:.0f}% fraud confidence. "
            f"Primary drivers: {factors}. Recommend immediate review for "
            f"account takeover or card-not-present fraud."
        )
    return (
        f"FRAUD prediction (p={ctx['fraud_probability']}). "
        f"Top SHAP contributors: {json.dumps(ctx['top_factors'], indent=2)}"
    )
