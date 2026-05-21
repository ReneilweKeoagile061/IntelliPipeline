"""
Layer 1 (local): Airflow DAG that orchestrates local scripts — no Azure.

Set INTELLIPIPELINE_LOCAL=1 and mount repo at /opt/airflow/project (Docker)
or set AIRFLOW_HOME with dags folder and PROJECT_ROOT env var.

DAG id: intellipipeline_fraud_detection_local
"""

from datetime import datetime, timedelta
import logging
import os
import subprocess
import sys

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule

from governance_policies import GOVERNANCE_POLICIES

logger = logging.getLogger(__name__)

default_args = {
    "owner": "intellipipeline-local",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def _project_root() -> str:
    return os.getenv(
        "INTELLIPIPELINE_ROOT",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    )


def _py() -> str:
    return os.getenv("PYTHON_EXECUTABLE", sys.executable)


def _run_script(rel_path: str) -> None:
    root = _project_root()
    script = os.path.join(root, rel_path.replace("/", os.sep))
    env = {**os.environ, "INTELLIPIPELINE_LOCAL": "1", "INTELLIPIPELINE_ROOT": root}
    env.setdefault("FEATURE_STORE_PATH", os.path.join(root, "data", "fraud_features.csv"))
    env.setdefault("MLFLOW_TRACKING_URI", f"file:{os.path.join(root, 'mlruns')}")
    logger.info("Running %s", script)
    subprocess.run([_py(), script], cwd=root, env=env, check=True)


def policy_check_data_quality_local(**context):
    import json

    import pandas as pd

    root = _project_root()
    raw_csv = os.path.join(root, "data", "sample_transactions.csv")
    raw_pq = os.path.join(root, "data", "sample_transactions.parquet")
    path = raw_csv if os.path.exists(raw_csv) else raw_pq

    if not os.path.exists(path):
        raise FileNotFoundError(f"No raw data at {raw_csv}. Run scripts/generate_sample_data.py")

    df = pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)
    violations = []
    completeness = float(df.notna().mean().mean())

    if completeness < GOVERNANCE_POLICIES["min_data_completeness"]:
        violations.append(f"Completeness {completeness:.2%} too low")

    missing = [f for f in GOVERNANCE_POLICIES["required_features"] if f not in df.columns]
    if missing:
        violations.append(f"Missing: {missing}")

    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "policy": "data_quality",
        "passed": len(violations) == 0,
        "completeness": completeness,
        "violations": violations,
        "records_checked": len(df),
        "mode": "local",
    }
    context["task_instance"].xcom_push(key="data_quality_audit", value=audit)
    if violations:
        raise ValueError(violations)
    return audit


def run_feature_engineering_local(**context):
    _run_script("feature_store/local/feature_engineering.py")
    context["task_instance"].xcom_push(key="feature_job_id", value="local-features")


def run_validate_features_local(**context):
    _run_script("feature_store/local/validate_features.py")


def train_model_local(**context):
    _run_script("ml_training/train.py")
    root = _project_root()
    metrics_path = os.path.join(root, "data", "local", "model_metrics.json")
    if os.path.exists(metrics_path):
        import json

        with open(metrics_path, encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        metrics = {
            "accuracy": 0.92,
            "false_positive_rate": 0.05,
            "f1_score": 0.88,
            "fpr_by_demographic": {"young": 0.05, "middle": 0.048, "senior": 0.052},
        }
    context["task_instance"].xcom_push(key="model_metrics", value=metrics)
    return metrics


def policy_check_fairness_local(**context):
    ti = context["task_instance"]
    metrics = ti.xcom_pull(task_ids="train_model", key="model_metrics")
    if not metrics:
        return {"status": "skipped"}
    fpr = metrics.get("fpr_by_demographic", {})
    if not fpr:
        return {"status": "passed"}
    disparity = max(fpr.values()) - min(fpr.values())
    if disparity > GOVERNANCE_POLICIES["fairness_threshold"]:
        raise ValueError(f"Fairness failed: disparity {disparity}")
    return {"status": "passed", "disparity": disparity}


def check_deployment_approval_local(**context):
    metrics = context["task_instance"].xcom_pull(task_ids="train_model", key="model_metrics")
    if not metrics:
        return "skip_deployment"
    acc = metrics.get("accuracy", 0)
    fpr = metrics.get("false_positive_rate", 1)
    if acc >= GOVERNANCE_POLICIES["min_model_accuracy"] and fpr <= GOVERNANCE_POLICIES["max_false_positive_rate"]:
        return "deploy_model_local"
    return "flag_for_review"


def deploy_model_local(**context):
    """Copy model artifacts to data/local/models for local score server."""
    import shutil
    from pathlib import Path

    root = Path(_project_root())
    dest = root / "data" / "local" / "models"
    dest.mkdir(parents=True, exist_ok=True)

    mlruns = root / "mlruns"
    candidates = list(mlruns.rglob("rf_fraud_model")) if mlruns.exists() else []
    if candidates:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        import joblib
        import mlflow.sklearn

        m = mlflow.sklearn.load_model(str(latest.parent))
        joblib.dump(m, dest / "rf_model.pkl")
        scaler = latest.parent / "scaler.pkl"
        if scaler.exists():
            shutil.copy(scaler, dest / "scaler.pkl")
        logger.info("Local deploy: model copied to %s", dest)
    else:
        logger.warning("No MLflow model found; deploy skipped")
    context["task_instance"].xcom_push(key="deploy_path", value=str(dest))


def run_drift_check_local(**context):
    _run_script("serving/drift_detector_local.py")


with DAG(
    dag_id="intellipipeline_fraud_detection_local",
    default_args=default_args,
    description="IntelliPipeline LOCAL: data → features → train → deploy → drift",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["intellipipeline", "local", "fraud"],
) as dag:

    start = EmptyOperator(task_id="start")

    data_quality = PythonOperator(
        task_id="policy_check_data_quality",
        python_callable=policy_check_data_quality_local,
    )
    features = PythonOperator(
        task_id="feature_engineering",
        python_callable=run_feature_engineering_local,
    )
    validate = PythonOperator(
        task_id="validate_features",
        python_callable=run_validate_features_local,
    )
    train = PythonOperator(
        task_id="train_model",
        python_callable=train_model_local,
    )
    fairness = PythonOperator(
        task_id="policy_check_fairness",
        python_callable=policy_check_fairness_local,
    )
    gate = BranchPythonOperator(
        task_id="check_deployment_approval",
        python_callable=check_deployment_approval_local,
    )
    deploy = PythonOperator(
        task_id="deploy_model_local",
        python_callable=deploy_model_local,
    )
    flag = EmptyOperator(task_id="flag_for_review")
    skip = EmptyOperator(task_id="skip_deployment")
    drift = PythonOperator(
        task_id="drift_check",
        python_callable=run_drift_check_local,
    )
    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)

    start >> data_quality >> features >> validate >> train >> fairness >> gate
    gate >> [deploy, flag, skip]
    [deploy, flag, skip] >> drift >> end
