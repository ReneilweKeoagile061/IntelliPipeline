# feature_store/notebooks/04_green_metrics.py
"""Aggregate and report Green MLOps metrics from Delta Lake feature runs."""

from pyspark.sql import functions as F

FEATURE_STORE_PATH = "abfss://features@stintellipipeline.dfs.core.windows.net/fraud_features"

history = spark.sql(f"DESCRIBE HISTORY delta.`{FEATURE_STORE_PATH}`")
history.select("version", "timestamp", "operationMetrics").show(truncate=False)

features_df = spark.read.format("delta").load(FEATURE_STORE_PATH)
summary = features_df.agg(
    F.count("*").alias("total_records"),
    F.max("feature_timestamp").alias("latest_feature_ts"),
).collect()[0]

print(f"Total feature records: {summary['total_records']:,}")
print(f"Latest feature timestamp: {summary['latest_feature_ts']}")
