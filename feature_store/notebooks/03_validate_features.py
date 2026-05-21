# feature_store/notebooks/03_validate_features.py
import json
import os

import great_expectations as ge
from great_expectations.dataset import SparkDFDataset
from pyspark.sql import functions as F

FEATURE_STORE_PATH = os.getenv(
    "FEATURE_STORE_PATH",
    "abfss://features@stintellipipeline.dfs.core.windows.net/fraud_features",
)

features_df = spark.read.format("delta").load(FEATURE_STORE_PATH)
ge_df = SparkDFDataset(features_df)

results = []

for col in ["customer_id", "transaction_amount", "is_fraud", "rule_based_risk"]:
    results.append(ge_df.expect_column_to_exist(col))

results.append(
    ge_df.expect_column_values_to_be_between(
        "transaction_amount", min_value=0.01, max_value=1_000_000
    )
)
results.append(
    ge_df.expect_column_values_to_be_between(
        "rule_based_risk", min_value=0.0, max_value=1.0
    )
)
results.append(
    ge_df.expect_column_mean_to_be_between("is_fraud", min_value=0.005, max_value=0.05)
)

for col in ["customer_id", "transaction_amount", "is_fraud"]:
    results.append(ge_df.expect_column_values_to_not_be_null(col))

conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if conn:
    from azure.storage.blob import BlobServiceClient

    blob_client = BlobServiceClient.from_connection_string(conn)
    try:
        baseline_bytes = (
            blob_client.get_blob_client("feature-baselines", "amount_distribution.json")
            .download_blob()
            .readall()
        )
        baseline = json.loads(baseline_bytes)
        stats = features_df.agg(
            F.mean("transaction_amount").alias("mean"),
            F.stddev("transaction_amount").alias("std"),
        ).collect()[0]
        mean_shift = abs(stats["mean"] - baseline["mean"]) / baseline["mean"]
        if mean_shift > 0.15:
            print(f"WARNING: Transaction amount distribution shifted {mean_shift:.1%}")
            mlflow.log_metric("feature_distribution_shift", mean_shift)
    except Exception:
        stats = features_df.agg(
            F.mean("transaction_amount").alias("mean"),
            F.stddev("transaction_amount").alias("std"),
        ).collect()[0]
        blob_client.get_blob_client(
            "feature-baselines", "amount_distribution.json"
        ).upload_blob(
            json.dumps({"mean": float(stats["mean"]), "std": float(stats["std"])}),
            overwrite=True,
        )
        print("Baseline distribution saved for future comparison")

failed = [r for r in results if not r.success]
print(f"Validation: {len(results) - len(failed)}/{len(results)} checks passed")

if failed:
    for f in failed:
        print(f"FAILED: {f.expectation_config.expectation_type}")
    raise ValueError(f"{len(failed)} validation checks failed — blocking pipeline")

print("All feature validation checks passed.")
