# Databricks notebook: ingest raw transactions into ADLS
# feature_store/notebooks/01_ingest_raw_data.py

from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("IntelliPipeline-Ingest")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .getOrCreate()
)

STORAGE_ACCOUNT = "stintellipipeline"
RAW_PATH = f"abfss://raw@{STORAGE_ACCOUNT}.dfs.core.windows.net/transactions"
SOURCE_PATH = f"abfss://ingest@{STORAGE_ACCOUNT}.dfs.core.windows.net/batch/"

raw_df = spark.read.parquet(SOURCE_PATH)
raw_df.write.mode("append").parquet(RAW_PATH)
print(f"Ingested {raw_df.count():,} transactions to {RAW_PATH}")
