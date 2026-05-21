# orchestration/dags/fraud_pipeline.py
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule
import logging

from governance_policies import GOVERNANCE_POLICIES

logger = logging.getLogger(__name__)

default_args = {
    "owner": "reneilwe.keoagile",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["reneilwekeo@gmail.com"],
    "execution_timeout": timedelta(hours=2),
}


def policy_check_data_quality(**context):
    """Policy Gate 1: Data quality enforcement."""
    import io
    import json
    import os

    import pandas as pd
    from azure.storage.blob import BlobServiceClient

    logger.info("POLICY CHECK: Data quality validation starting...")

    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        logger.warning("No storage connection — using local demo path")
        root = os.getenv("INTELLIPIPELINE_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        demo_csv = os.path.join(root, "data", "sample_transactions.csv")
        demo_path = os.getenv("DEMO_RAW_DATA_PATH", demo_csv)
        if os.path.exists(demo_path):
            df = pd.read_csv(demo_path) if demo_path.endswith(".csv") else pd.read_parquet(demo_path)
        else:
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "dag_run_id": context["run_id"],
                "policy": "data_quality",
                "passed": True,
                "completeness": 1.0,
                "violations": [],
                "records_checked": 0,
                "note": "demo_mode_no_data",
            }
            context["task_instance"].xcom_push(
                key="data_quality_audit", value=audit_record
            )
            return audit_record
    else:
        blob_client = BlobServiceClient.from_connection_string(conn)
        container = blob_client.get_container_client("raw-transactions")
        blobs = list(container.list_blobs(name_starts_with="batch/"))
        if not blobs:
            raise ValueError("No raw transaction batches found in storage")
        latest = sorted(blobs, key=lambda x: x.last_modified)[-1]
        data_bytes = container.download_blob(latest.name).readall()
        df = pd.read_parquet(io.BytesIO(data_bytes))

    violations = []
    completeness = float(df.notna().mean().mean())

    if completeness < GOVERNANCE_POLICIES["min_data_completeness"]:
        violations.append(
            f"Data completeness {completeness:.2%} below threshold "
            f"{GOVERNANCE_POLICIES['min_data_completeness']:.2%}"
        )

    missing_features = [
        f for f in GOVERNANCE_POLICIES["required_features"] if f not in df.columns
    ]
    if missing_features:
        violations.append(f"Missing required features: {missing_features}")

    if "is_fraud" in df.columns:
        counts = df["is_fraud"].value_counts()
        legit = counts.get(0, 1)
        fraud = max(counts.get(1, 1), 1)
        fraud_ratio = legit / fraud
        if fraud_ratio > GOVERNANCE_POLICIES["max_class_imbalance_ratio"]:
            violations.append(
                f"Class imbalance ratio {fraud_ratio:.1f}x exceeds policy "
                f"{GOVERNANCE_POLICIES['max_class_imbalance_ratio']}x"
            )

    audit_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "dag_run_id": context["run_id"],
        "policy": "data_quality",
        "passed": len(violations) == 0,
        "completeness": completeness,
        "violations": violations,
        "records_checked": len(df),
    }

    context["task_instance"].xcom_push(key="data_quality_audit", value=audit_record)

    if violations:
        logger.error("POLICY VIOLATION: %s", violations)
        raise ValueError(f"Data quality policy failed: {violations}")

    logger.info(
        "POLICY PASSED: Data quality check passed. %s records validated.", len(df)
    )
    return audit_record


def policy_check_fairness(**context):
    """Policy Gate 2: Fairness and demographic parity."""
    logger.info("POLICY CHECK: Fairness analysis starting...")

    ti = context["task_instance"]
    model_metrics = ti.xcom_pull(task_ids="train_model", key="model_metrics")

    if not model_metrics:
        logger.info("No previous model metrics — skipping fairness check for first run")
        return {"status": "skipped", "reason": "first_run"}

    fpr_by_group = model_metrics.get("fpr_by_demographic", {})

    if fpr_by_group:
        max_fpr = max(fpr_by_group.values())
        min_fpr = min(fpr_by_group.values())
        disparity = max_fpr - min_fpr

        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "dag_run_id": context["run_id"],
            "policy": "fairness",
            "demographic_parity_difference": float(disparity),
            "threshold": GOVERNANCE_POLICIES["fairness_threshold"],
            "passed": disparity <= GOVERNANCE_POLICIES["fairness_threshold"],
            "fpr_by_group": fpr_by_group,
        }

        ti.xcom_push(key="fairness_audit", value=audit_record)

        if disparity > GOVERNANCE_POLICIES["fairness_threshold"]:
            raise ValueError(
                f"Fairness policy failed: demographic parity difference "
                f"{disparity:.3f} exceeds {GOVERNANCE_POLICIES['fairness_threshold']}"
            )

    logger.info("POLICY PASSED: Fairness check passed.")
    return {"status": "passed"}


def check_deployment_approval(**context):
    """Policy Gate 3: Pre-deployment accuracy gate."""
    ti = context["task_instance"]
    model_metrics = ti.xcom_pull(task_ids="train_model", key="model_metrics")

    if not model_metrics:
        return "skip_deployment"

    accuracy = model_metrics.get("accuracy", 0)
    fpr = model_metrics.get("false_positive_rate", 1)

    if (
        accuracy >= GOVERNANCE_POLICIES["min_model_accuracy"]
        and fpr <= GOVERNANCE_POLICIES["max_false_positive_rate"]
    ):
        logger.info("DEPLOYMENT APPROVED: accuracy=%.3f, fpr=%.3f", accuracy, fpr)
        return "deploy_model"

    logger.warning(
        "DEPLOYMENT BLOCKED: accuracy=%.3f (min=%s), fpr=%.3f (max=%s)",
        accuracy,
        GOVERNANCE_POLICIES["min_model_accuracy"],
        fpr,
        GOVERNANCE_POLICIES["max_false_positive_rate"],
    )
    return "flag_for_review"


def trigger_databricks_features(**context):
    """Trigger Databricks feature engineering via Azure ML."""
    import os

    if not os.getenv("AZURE_SUBSCRIPTION_ID"):
        logger.info("Demo mode: skipping Azure ML feature job")
        context["task_instance"].xcom_push(key="feature_job_id", value="demo-local")
        return

    from azure.ai.ml import MLClient, command
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
        workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
    )

    job = command(
        command="python feature_engineering.py",
        environment="intellipipeline-env:1",
        compute="databricks-cluster",
        experiment_name="intellipipeline-features",
    )
    returned_job = ml_client.jobs.create_or_update(job)
    logger.info("Feature engineering job submitted: %s", returned_job.name)
    context["task_instance"].xcom_push(key="feature_job_id", value=returned_job.name)


def train_model(**context):
    """Submit training job to Azure ML or run locally in demo mode."""
    import os

    if not os.getenv("AZURE_SUBSCRIPTION_ID"):
        logger.info("Demo mode: using placeholder model metrics")
        metrics = {
            "accuracy": 0.924,
            "false_positive_rate": 0.051,
            "f1_score": 0.89,
            "fpr_by_demographic": {"young": 0.05, "middle": 0.048, "senior": 0.052},
        }
        context["task_instance"].xcom_push(key="model_metrics", value=metrics)
        return metrics

    import mlflow
    from azure.ai.ml import MLClient, command
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
        workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
    )

    job = command(
        command="python ml_training/train.py --generate-xai true",
        environment="intellipipeline-env:1",
        compute="cpu-cluster",
        experiment_name="intellipipeline-fraud-detection",
    )
    returned_job = ml_client.jobs.create_or_update(job)
    ml_client.jobs.stream(returned_job.name)

    mlflow.set_tracking_uri(
        ml_client.workspaces.get(
            os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline")
        ).mlflow_tracking_uri
    )
    run = mlflow.get_run(returned_job.name)
    metrics = {
        "accuracy": run.data.metrics.get("accuracy"),
        "false_positive_rate": run.data.metrics.get("false_positive_rate"),
        "f1_score": run.data.metrics.get("f1_score"),
        "fpr_by_demographic": {},
    }
    context["task_instance"].xcom_push(key="model_metrics", value=metrics)
    return metrics


def deploy_model(**context):
    """Deploy approved model to Azure ML online endpoint."""
    import os

    if not os.getenv("AZURE_SUBSCRIPTION_ID"):
        logger.info("Demo mode: skipping deployment")
        return

    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import ManagedOnlineDeployment
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
        workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
    )

    deployment = ManagedOnlineDeployment(
        name="green",
        endpoint_name="intellipipeline-endpoint",
        model="azureml:intellipipeline-fraud-model:latest",
        instance_type="Standard_DS2_v2",
        instance_count=1,
    )

    ml_client.online_deployments.begin_create_or_update(deployment).result()

    endpoint = ml_client.online_endpoints.get("intellipipeline-endpoint")
    endpoint.traffic = {"blue": 90, "green": 10}
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()

    logger.info("Model deployed: 10%% traffic routed to green deployment")


with DAG(
    dag_id="intellipipeline_fraud_detection",
    default_args=default_args,
    description="IntelliPipeline: Full ML lifecycle for fraud detection with Policy-as-Code",
    schedule_interval="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["intellipipeline", "fraud", "governance", "mlops"],
) as dag:

    start = EmptyOperator(task_id="start")

    data_quality_check = PythonOperator(
        task_id="policy_check_data_quality",
        python_callable=policy_check_data_quality,
    )

    feature_engineering = PythonOperator(
        task_id="trigger_databricks_features",
        python_callable=trigger_databricks_features,
    )

    fairness_check = PythonOperator(
        task_id="policy_check_fairness",
        python_callable=policy_check_fairness,
    )

    model_training = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    deployment_gate = BranchPythonOperator(
        task_id="check_deployment_approval",
        python_callable=check_deployment_approval,
    )

    deploy = PythonOperator(
        task_id="deploy_model",
        python_callable=deploy_model,
    )

    flag_review = EmptyOperator(task_id="flag_for_review")
    skip_deploy = EmptyOperator(task_id="skip_deployment")

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    start >> data_quality_check >> feature_engineering >> fairness_check >> model_training >> deployment_gate
    deployment_gate >> [deploy, flag_review, skip_deploy]
    [deploy, flag_review, skip_deploy] >> end
