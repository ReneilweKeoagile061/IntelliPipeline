# IntelliPipeline on Databricks

**Repo on Databricks:** `/Workspace/Users/reneilwekeo@gmail.com/IntelliPipeline`  
**GitHub:** [github.com/ReneilweKeoagile061/IntelliPipeline](https://github.com/ReneilweKeoagile061/IntelliPipeline)

---

## Environment (your cluster)

| Package | Version |
|---------|---------|
| Python | 3.12.3 |
| pandas | 2.2.3 |
| scikit-learn | 1.6.1 |
| MLflow | 3.8.1 |
| PySpark | 4.1.0 |
| Delta | 3.4.0 |

Install extras in a notebook cell:

```python
%pip install shap great-expectations
```

---

## Week 1 — One notebook (recommended)

Open and run:

**`notebooks/databricks/IntelliPipeline_Week1_E2E.py`**

Import to Databricks: **Workspace → Import → File** or sync from Git folder.

### What it runs

| Option | Description |
|--------|-------------|
| **A** | 100K synthetic fraud transactions → Delta `raw_transactions` |
| **D** | Windowed features → Delta `fraud_features` + `DESCRIBE HISTORY` |
| **B** | Random Forest + SHAP → Databricks MLflow experiment |
| **C** | PSI / KL drift + simulated retrain signal |
| **E** | Checklist summary |

### Paths (default)

```
/tmp/intellipipeline/raw_transactions
/tmp/intellipipeline/fraud_features
/tmp/intellipipeline/artifacts/
```

Override:

```python
%env INTELLIPIPELINE_DELTA_BASE=/Volumes/catalog/schema/intellipipeline
%env INTELLIPIPELINE_N_RECORDS=100000
```

---

## Run repo scripts from Databricks

```python
%cd /Workspace/Users/reneilwekeo@gmail.com/IntelliPipeline
%pip install -r requirements-local.txt -q

# Option: use local pandas pipeline (no Spark)
%run ./scripts/generate_sample_data.py
%run ./feature_store/local/feature_engineering.py
%run ./ml_training/train.py
```

For Spark/Delta, use the Week 1 notebook instead of `feature_store/local/`.

---

## MLflow

The notebook sets:

```python
mlflow.set_experiment("/Users/reneilwekeo@gmail.com/intellipipeline-fraud-detection")
```

View runs: **Machine Learning → Experiments** in Databricks.

---

## Target metrics (portfolio narrative)

| Metric | Before | Target |
|--------|--------|--------|
| Fraud accuracy | 71.4% | 92.4% |
| False positive rate | 14.2% | 5.1% |
| Adaptation time | 38.6 days | 9.7 days |

Your Week 1 run should report **achieved** metrics in the notebook summary table; tune data/model to approach targets.

---

## After Week 1

| Week | Task |
|------|------|
| 2 | Register best model in Unity Catalog / Model Registry |
| 3 | Airflow `fraud_pipeline_local` or Jobs orchestration |
| 4 | Scheduled drift job → trigger retraining |
| 5 | Deploy API + dashboard |
| 6 | Port Delta paths to ADLS (`abfss://`) per Azure guide |

See [LOCAL_BUILD.md](LOCAL_BUILD.md) for the local-first path; use Databricks for Delta + MLflow at scale.
