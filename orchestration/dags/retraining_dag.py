# orchestration/dags/retraining_dag.py
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

default_args = {"owner": "intellipipeline", "retries": 1}


def check_retraining_signal(**context):
    """
    Reads drift signals from Azure Blob Storage.
    Retrain if PSI > 0.25 AND (accuracy dropped > 2% OR KL > 0.1).
    """
    import json
    import os

    from azure.storage.blob import BlobServiceClient

    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        signal = {
            "psi": 0.0,
            "kl_divergence": 0.0,
            "accuracy_drop": 0.0,
            "should_retrain": False,
            "trigger_timestamp": datetime.utcnow().isoformat(),
            "note": "demo_mode_no_storage",
        }
        context["task_instance"].xcom_push(key="retrain_signal", value=signal)
        return signal

    blob_client = BlobServiceClient.from_connection_string(conn)
    container = blob_client.get_container_client("drift-signals")

    blobs = list(container.list_blobs())
    if not blobs:
        return {"action": "no_action", "reason": "no drift signals found"}

    latest = sorted(blobs, key=lambda x: x.last_modified)[-1]
    drift_data = json.loads(container.download_blob(latest.name).readall())

    psi = drift_data.get("psi_score", 0)
    kl_div = drift_data.get("kl_divergence", 0)
    accuracy_drop = drift_data.get("accuracy_drop", 0)

    should_retrain = psi > 0.25 and (accuracy_drop > 0.02 or kl_div > 0.1)

    signal = {
        "psi": psi,
        "kl_divergence": kl_div,
        "accuracy_drop": accuracy_drop,
        "should_retrain": should_retrain,
        "trigger_timestamp": datetime.utcnow().isoformat(),
    }

    context["task_instance"].xcom_push(key="retrain_signal", value=signal)
    return signal


with DAG(
    dag_id="intellipipeline_auto_retrain",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["intellipipeline", "retraining", "drift"],
) as dag:

    check_signal = PythonOperator(
        task_id="check_retraining_signal",
        python_callable=check_retraining_signal,
    )

    trigger_pipeline = TriggerDagRunOperator(
        task_id="trigger_main_pipeline",
        trigger_dag_id="intellipipeline_fraud_detection",
        conf={"trigger_reason": "drift_detected"},
    )

    check_signal >> trigger_pipeline
