# feature_store/notebooks/02_feature_engineering.py
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
import time

spark = (
    SparkSession.builder.appName("IntelliPipeline-FeatureEngineering")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .getOrCreate()
)

STORAGE_ACCOUNT = "stintellipipeline"
FEATURE_STORE_PATH = (
    f"abfss://features@{STORAGE_ACCOUNT}.dfs.core.windows.net/fraud_features"
)
RAW_DATA_PATH = f"abfss://raw@{STORAGE_ACCOUNT}.dfs.core.windows.net/transactions"

compute_start = time.time()
raw_df = spark.read.parquet(RAW_DATA_PATH)
print(f"Loaded {raw_df.count():,} raw transactions")

customer_window_7d = (
    Window.partitionBy("customer_id")
    .orderBy("transaction_timestamp")
    .rangeBetween(-7 * 86400, 0)
)
customer_window_30d = (
    Window.partitionBy("customer_id")
    .orderBy("transaction_timestamp")
    .rangeBetween(-30 * 86400, 0)
)

features_df = (
    raw_df.withColumn("tx_count_7d", F.count("transaction_id").over(customer_window_7d))
    .withColumn("avg_amount_30d", F.avg("transaction_amount").over(customer_window_30d))
    .withColumn(
        "amount_deviation_ratio",
        F.col("transaction_amount") / (F.col("avg_amount_30d") + F.lit(0.01)),
    )
    .withColumn("hour_of_day", F.hour(F.col("transaction_timestamp")))
    .withColumn(
        "is_weekend",
        (F.dayofweek(F.col("transaction_timestamp")).isin([1, 7])).cast("integer"),
    )
    .withColumn(
        "is_new_merchant",
        (F.count("merchant_id").over(customer_window_30d) == 1).cast("integer"),
    )
    .withColumn(
        "is_cross_border",
        (F.col("merchant_country") != F.col("customer_country")).cast("integer"),
    )
    .withColumn(
        "rule_based_risk",
        F.col("amount_deviation_ratio") * 0.3
        + F.col("is_new_merchant") * 0.25
        + F.col("is_cross_border") * 0.25
        + F.when(F.col("tx_count_7d") > 20, 1.0).otherwise(0.0) * 0.2,
    )
    .withColumn("feature_version", F.lit("v1.0"))
    .withColumn("feature_timestamp", F.current_timestamp())
)

FEATURE_COLUMNS = [
    "customer_id",
    "transaction_id",
    "transaction_timestamp",
    "transaction_amount",
    "merchant_category",
    "merchant_country",
    "customer_country",
    "device_fingerprint",
    "tx_count_7d",
    "avg_amount_30d",
    "amount_deviation_ratio",
    "hour_of_day",
    "is_weekend",
    "is_new_merchant",
    "is_cross_border",
    "rule_based_risk",
    "is_fraud",
    "feature_version",
    "feature_timestamp",
]

final_features = features_df.select(FEATURE_COLUMNS)
final_features.write.format("delta").mode("append").option(
    "mergeSchema", "true"
).partitionBy("feature_version").save(FEATURE_STORE_PATH)

record_count = final_features.count()
print(f"Written {record_count:,} feature records to Delta Lake")

compute_duration_seconds = time.time() - compute_start
parallelism = spark.sparkContext.defaultParallelism or 4
estimated_kwh = (compute_duration_seconds / 3600) * 0.095 * parallelism
green_metrics = {
    "compute_duration_seconds": compute_duration_seconds,
    "estimated_energy_kwh": estimated_kwh,
    "estimated_co2_grams": estimated_kwh * 475,
    "records_processed": record_count,
    "efficiency_records_per_kwh": record_count / max(estimated_kwh, 0.001),
}

import mlflow

mlflow.log_metrics(
    {
        "energy_kwh": green_metrics["estimated_energy_kwh"],
        "co2_grams": green_metrics["estimated_co2_grams"],
        "compute_seconds": green_metrics["compute_duration_seconds"],
    }
)
print(
    f"Green Metrics: {estimated_kwh:.4f} kWh | "
    f"{green_metrics['estimated_co2_grams']:.2f}g CO2"
)
