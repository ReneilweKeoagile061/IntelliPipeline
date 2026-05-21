# Databricks notebook source
# MAGIC %md
# MAGIC # IntelliPipeline — Week 1 End-to-End (Databricks)
# MAGIC **Author:** Reneilwe Keoagile · [GitHub](https://github.com/ReneilweKeoagile061/IntelliPipeline)
# MAGIC
# MAGIC Run all cells top-to-bottom for: **synthetic data → Delta features → train + SHAP → drift detection → MLflow**
# MAGIC
# MAGIC | Step | Layer | Output |
# MAGIC |------|-------|--------|
# MAGIC | A | Data | Raw transactions (Delta) |
# MAGIC | B | Feature store | `fraud_features` Delta table |
# MAGIC | C | Training | MLflow run + XAI report |
# MAGIC | D | Drift | PSI / KL + retrain signal |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# MAGIC %pip install shap great-expectations -q

# COMMAND ----------

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# Repo path on Databricks (adjust if your clone path differs)
REPO_ROOT = "/Workspace/Users/reneilwekeo@gmail.com/IntelliPipeline"
if not os.path.exists(REPO_ROOT):
    REPO_ROOT = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

# Delta paths (DBFS — change to Unity Catalog volume if you use one)
DELTA_BASE = os.environ.get("INTELLIPIPELINE_DELTA_BASE", "/tmp/intellipipeline")
RAW_DELTA = f"{DELTA_BASE}/raw_transactions"
FEATURE_DELTA = f"{DELTA_BASE}/fraud_features"
ARTIFACTS_PATH = f"{DELTA_BASE}/artifacts"

N_RECORDS = int(os.environ.get("INTELLIPIPELINE_N_RECORDS", "100000"))
RANDOM_SEED = 42

print(f"Repo: {REPO_ROOT}")
print(f"Delta base: {DELTA_BASE}")
print(f"Records: {N_RECORDS:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option A — Generate synthetic fraud data (100K)

# COMMAND ----------

np.random.seed(RANDOM_SEED)
N = N_RECORDS
n_fraud = int(N * 0.03)
is_fraud = np.zeros(N, dtype=int)
is_fraud[:n_fraud] = 1
np.random.shuffle(is_fraud)

raw_pdf = pd.DataFrame(
    {
        "customer_id": [f"C{i % 5000:05d}" for i in range(N)],
        "transaction_id": [f"TX-{i:08d}" for i in range(N)],
        "transaction_timestamp": pd.date_range("2024-01-01", periods=N, freq="1min"),
        "transaction_amount": np.round(
            np.random.lognormal(4, 1.2, N) * (1 + is_fraud * 0.5), 2
        ),
        "merchant_category": np.random.choice(
            ["retail", "grocery", "travel", "electronics", "cash_advance"], N
        ),
        "merchant_id": [f"M{np.random.randint(1, 500):04d}" for _ in range(N)],
        "merchant_country": np.random.choice(
            ["BW", "ZA", "US", "GB"], N, p=[0.6, 0.2, 0.1, 0.1]
        ),
        "customer_country": np.random.choice(["BW", "ZA"], N, p=[0.85, 0.15]),
        "customer_age_days": np.random.randint(30, 3650, N),
        "device_fingerprint": [f"DEV-{np.random.randint(1000, 9999)}" for _ in range(N)],
        "hour_of_day": np.random.randint(0, 24, N),
        "is_fraud": is_fraud,
    }
)

raw_sdf = spark.createDataFrame(raw_pdf)
(
    raw_sdf.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .save(RAW_DELTA)
)

print(f"Raw transactions: {raw_sdf.count():,} rows → {RAW_DELTA}")
display(raw_sdf.groupBy("is_fraud").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option D — Delta Lake feature store (windowed features)

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

raw_df = spark.read.format("delta").load(RAW_DELTA)
raw_df = raw_df.withColumn("transaction_timestamp", F.col("transaction_timestamp").cast("timestamp"))

w7 = Window.partitionBy("customer_id").orderBy(F.col("transaction_timestamp").cast("long")).rangeBetween(-7 * 86400, 0)
w30 = Window.partitionBy("customer_id").orderBy(F.col("transaction_timestamp").cast("long")).rangeBetween(-30 * 86400, 0)

features_df = (
    raw_df.withColumn("tx_count_7d", F.count("transaction_id").over(w7))
    .withColumn("avg_amount_30d", F.avg("transaction_amount").over(w30))
    .withColumn(
        "amount_deviation_ratio",
        F.col("transaction_amount") / (F.col("avg_amount_30d") + F.lit(0.01)),
    )
    .withColumn("hour_of_day", F.hour("transaction_timestamp"))
    .withColumn(
        "is_weekend",
        F.when(F.dayofweek("transaction_timestamp").isin(1, 7), 1).otherwise(0),
    )
    .withColumn(
        "is_new_merchant",
        F.when(F.count("merchant_id").over(w30) == 1, 1).otherwise(0),
    )
    .withColumn(
        "is_cross_border",
        F.when(F.col("merchant_country") != F.col("customer_country"), 1).otherwise(0),
    )
    .withColumn(
        "rule_based_risk",
        (
            F.col("amount_deviation_ratio") * 0.3
            + F.col("is_new_merchant") * 0.25
            + F.col("is_cross_border") * 0.25
            + F.when(F.col("tx_count_7d") > 20, 1.0).otherwise(0.0) * 0.2
        ),
    )
    .withColumn("feature_version", F.lit("v1.0-databricks"))
    .withColumn("feature_timestamp", F.current_timestamp())
)

feature_cols = [
    "customer_id", "transaction_id", "transaction_timestamp", "transaction_amount",
    "merchant_category", "merchant_country", "customer_country", "device_fingerprint",
    "tx_count_7d", "avg_amount_30d", "amount_deviation_ratio", "hour_of_day",
    "is_weekend", "is_new_merchant", "is_cross_border", "rule_based_risk",
    "is_fraud", "feature_version", "feature_timestamp",
]
final_features = features_df.select(feature_cols)

(
    final_features.write.format("delta")
    .mode("overwrite")
    .option("mergeSchema", "true")
    .partitionBy("feature_version")
    .save(FEATURE_DELTA)
)

print(f"Features written: {final_features.count():,} → {FEATURE_DELTA}")
display(spark.sql(f"DESCRIBE HISTORY delta.`{FEATURE_DELTA}`").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Feature validation (Great Expectations)

# COMMAND ----------

try:
    from great_expectations.dataset import SparkDFDataset

    ge_df = SparkDFDataset(final_features)
    checks = [
        ge_df.expect_column_to_exist("is_fraud"),
        ge_df.expect_column_values_to_be_between("transaction_amount", 0.01, 1_000_000),
        ge_df.expect_column_values_to_be_between("rule_based_risk", 0.0, 1.0),
        ge_df.expect_column_mean_to_be_between("is_fraud", 0.005, 0.05),
    ]
    failed = [c for c in checks if not c.success]
    print(f"Validation: {len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        raise ValueError(f"{len(failed)} GE checks failed")
except ImportError:
    print("Great Expectations not available — skipping GE (install with %pip)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option B — Train model + XAI (MLflow on Databricks)

# COMMAND ----------

import mlflow
import mlflow.sklearn
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "transaction_amount", "tx_count_7d", "avg_amount_30d", "amount_deviation_ratio",
    "hour_of_day", "is_weekend", "is_new_merchant", "is_cross_border", "rule_based_risk",
]

pdf = final_features.toPandas()
X = pdf[FEATURE_COLS]
y = pdf["is_fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
)
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

experiment = "/intellipipeline-fraud-detection"
try:
    mlflow.set_experiment(experiment)
except Exception:
    mlflow.create_experiment(experiment)
    mlflow.set_experiment(experiment)

with mlflow.start_run(run_name="databricks-week1-rf") as run:
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=15, class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1
    )
    rf.fit(X_train_s, y_train)
    y_pred = rf.predict(X_test_s)
    y_prob = rf.predict_proba(X_test_s)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    mlflow.log_metrics({
        "accuracy": accuracy, "f1_score": f1, "roc_auc": auc,
        "false_positive_rate": fpr, "true_positive_rate": tp / (tp + fn) if (tp + fn) else 0,
    })

    explainer = shap.TreeExplainer(rf)
    idx = np.random.choice(len(X_test_s), min(200, len(X_test_s)), replace=False)
    shap_vals = explainer.shap_values(X_test_s[idx])
    shap_arr = np.asarray(shap_vals[-1] if isinstance(shap_vals, list) else shap_vals)
    if shap_arr.ndim == 3:
        shap_arr = shap_arr[:, :, 1]
    mean_shap = np.abs(shap_arr).mean(axis=0).flatten()
    feature_importance = {n: float(v) for n, v in zip(FEATURE_COLS, mean_shap)}

    xai_report = {
        "feature_importance": feature_importance,
        "top_features": sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5],
        "methodology": "SHAP TreeExplainer",
        "run_id": run.info.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    dbutils.fs.mkdirs(ARTIFACTS_PATH)
    dbutils.fs.put(
        f"{ARTIFACTS_PATH}/xai_report.json",
        json.dumps(xai_report, indent=2),
        overwrite=True,
    )

    mlflow.sklearn.log_model(rf, "rf_fraud_model")
    mlflow.log_dict(xai_report, "xai_report.json")

    print(f"Accuracy: {accuracy:.4f} | F1: {f1:.4f} | FPR: {fpr:.4f}")
    print(f"Top feature: {xai_report['top_features'][0]}")
    print(f"MLflow run: {run.info.run_id}")

# Target metrics reference
metrics_summary = pd.DataFrame({
    "metric": ["Accuracy", "FPR", "F1", "AUC"],
    "achieved": [accuracy, fpr, f1, auc],
    "target": [0.924, 0.051, None, None],
})
display(metrics_summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option C — Drift detection (PSI + KL)

# COMMAND ----------

def compute_psi(baseline, current, buckets=10):
    b_counts, edges = np.histogram(baseline, bins=buckets)
    c_counts, _ = np.histogram(current, bins=edges)
    b_pct = (b_counts + 1e-6) / len(baseline)
    c_pct = (c_counts + 1e-6) / len(current)
    return float(np.sum((c_pct - b_pct) * np.log(c_pct / b_pct)))


def compute_kl(baseline, current):
    from scipy.stats import entropy
    b_hist, edges = np.histogram(baseline, bins=20, density=True)
    c_hist, _ = np.histogram(current, bins=edges, density=True)
    return float(entropy(c_hist + 1e-10, b_hist + 1e-10))


baseline_scores = y_prob
np.random.seed(99)
simulated_drift = np.random.beta(5, 3, len(baseline_scores))

psi_normal = compute_psi(baseline_scores, baseline_scores + np.random.normal(0, 0.02, len(baseline_scores)))
psi_drift = compute_psi(baseline_scores, simulated_drift)
kl_drift = compute_kl(baseline_scores, simulated_drift)

drift_report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "psi_score_normal": psi_normal,
    "psi_score_simulated": psi_drift,
    "kl_divergence": kl_drift,
    "drift_detected": psi_drift > 0.25,
    "should_retrain": psi_drift > 0.25 and kl_drift > 0.1,
    "severity": "HIGH" if psi_drift > 0.25 else "MEDIUM" if psi_drift > 0.1 else "LOW",
}

dbutils.fs.put(f"{ARTIFACTS_PATH}/drift_report.json", json.dumps(drift_report, indent=2), overwrite=True)
print(json.dumps(drift_report, indent=2))
if drift_report["should_retrain"]:
    print("RETRAIN SIGNAL — would trigger intellipipeline_auto_retrain DAG in production")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option E — Week 1 checklist

# COMMAND ----------

checklist = pd.DataFrame([
    {"step": "A — Raw data", "path": RAW_DELTA, "status": "done"},
    {"step": "D — Delta features", "path": FEATURE_DELTA, "status": "done"},
    {"step": "B — Train + XAI", "path": f"MLflow experiment", "status": "done"},
    {"step": "C — Drift", "path": f"{ARTIFACTS_PATH}/drift_report.json", "status": "done"},
])
display(checklist)

print("\nNext: Week 3 — import orchestration/dags/fraud_pipeline_local.py into Airflow")
print("Week 5 — Flask API + React dashboard (see docs/LOCAL_BUILD.md)")
