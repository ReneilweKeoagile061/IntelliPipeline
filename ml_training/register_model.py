# ml_training/register_model.py
"""Manually register an MLflow run to Azure ML Model Registry."""

import argparse
import os

import mlflow

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", required=True)
parser.add_argument("--model-name", default="intellipipeline-fraud-model")
args = parser.parse_args()

from azure.ai.ml import MLClient
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential

ml_client = MLClient(
    credential=DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "rg-intellipipeline"),
    workspace_name=os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline"),
)

mlflow.set_tracking_uri(
    ml_client.workspaces.get(
        os.getenv("AZURE_ML_WORKSPACE", "mlw-intellipipeline")
    ).mlflow_tracking_uri
)

model = ml_client.models.create_or_update(
    Model(
        path=f"runs:/{args.run_id}/rf_fraud_model",
        name=args.model_name,
        type=AssetTypes.MLFLOW_MODEL,
    )
)
print(f"Registered {args.model_name} version {model.version}")
