# api/routes/drift.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, jsonify

drift_bp = Blueprint("drift", __name__)


def _demo_drift():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "psi_score": 0.12,
        "kl_divergence": 0.04,
        "accuracy_drop": 0.008,
        "drift_detected": False,
        "severity": "LOW",
        "baseline_mean": 0.18,
        "current_mean": 0.21,
        "history": [
            {"date": "Mon", "psi": 0.05},
            {"date": "Tue", "psi": 0.07},
            {"date": "Wed", "psi": 0.08},
            {"date": "Thu", "psi": 0.1},
            {"date": "Fri", "psi": 0.09},
            {"date": "Sat", "psi": 0.11},
            {"date": "Sun", "psi": 0.12},
        ],
    }


@drift_bp.route("/api/drift", methods=["GET"])
def get_drift():
    local_latest = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "local"
        / "drift_signals"
        / "latest_drift.json"
    )
    if local_latest.exists() or os.getenv("INTELLIPIPELINE_LOCAL") == "1":
        if local_latest.exists():
            report = json.loads(local_latest.read_text(encoding="utf-8"))
            history_dir = local_latest.parent
            history = []
            for p in sorted(history_dir.glob("drift_*.json"))[-7:]:
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    history.append(
                        {"date": p.stem.replace("drift_", "")[:8], "psi": d.get("psi_score", 0)}
                    )
                except Exception:
                    pass
            report["history"] = history or _demo_drift()["history"]
            return jsonify(report)

    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        return jsonify(_demo_drift())

    try:
        from azure.storage.blob import BlobServiceClient

        blob_client = BlobServiceClient.from_connection_string(conn)
        container = blob_client.get_container_client("drift-signals")
        blobs = sorted(
            list(container.list_blobs()),
            key=lambda x: x.last_modified,
            reverse=True,
        )[:7]

        history = []
        latest = None
        for b in reversed(blobs):
            data = json.loads(
                container.download_blob(b.name).readall().decode("utf-8")
            )
            history.append(
                {
                    "date": b.name.replace("drift_", "")[:8],
                    "psi": data.get("psi_score", 0),
                }
            )
            latest = data

        if latest:
            latest["history"] = history
            return jsonify(latest)
    except Exception:
        pass

    return jsonify(_demo_drift())
