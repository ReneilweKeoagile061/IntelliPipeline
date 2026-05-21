"""Shared paths for local (offline) IntelliPipeline development."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOCAL = DATA / "local"
ARTIFACTS = LOCAL / "artifacts"
DRIFT_DIR = LOCAL / "drift_signals"
BASELINES_DIR = LOCAL / "baselines"
PREDICTIONS_DIR = LOCAL / "prediction_logs"
MLRUNS = ROOT / "mlruns"
MODELS_DIR = LOCAL / "models"

RAW_CSV = DATA / "sample_transactions.csv"
RAW_PARQUET = DATA / "sample_transactions.parquet"
FEATURES_CSV = DATA / "fraud_features.csv"
FEATURES_PARQUET = DATA / "fraud_features.parquet"
XAI_REPORT = DATA / "xai_report.json"
METRICS_JSON = LOCAL / "model_metrics.json"
GREEN_METRICS_JSON = LOCAL / "green_metrics.json"

for d in (DATA, LOCAL, ARTIFACTS, DRIFT_DIR, BASELINES_DIR, PREDICTIONS_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def resolve_features_path() -> Path:
    if FEATURES_CSV.exists():
        return FEATURES_CSV
    if FEATURES_PARQUET.exists():
        return FEATURES_PARQUET
    return FEATURES_CSV


def resolve_raw_path() -> Path:
    if RAW_CSV.exists():
        return RAW_CSV
    if RAW_PARQUET.exists():
        return RAW_PARQUET
    return RAW_CSV
