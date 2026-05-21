# IntelliPipeline — Local Build Guide (Path B: Lite)

Azure is a **deployment target**, not a development dependency. Follow this order to get an interview-ready demo on your laptop in ~4 weeks.

---

## Build order

| Week | Layer | What to run | Done when |
|------|-------|-------------|-----------|
| **1** | Data | `python scripts/generate_sample_data.py` | `data/fraud_features.csv` exists |
| **2** | Features + ML | `feature_store/local/*.py` + `ml_training/train.py` | `mlruns/`, `data/local/model_metrics.json` |
| **3** | Airflow | `intellipipeline_fraud_detection_local` DAG | DAG green in UI at :8080 |
| **4** | Drift | `serving/drift_detector_local.py` | `data/local/drift_signals/latest_drift.json` |
| **5** | UI | `api/app.py` + `dashboard` npm dev | Dashboard shows live metrics |
| **6** | Azure | Port containers + one ML workspace demo | Optional |
| **7** | Polish | README, diagram, 2-min demo video | Portfolio ready |

---

## Week 1 — One-command setup

```powershell
cd IntelliPipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt

copy .env.example .env
# Set INTELLIPIPELINE_LOCAL=1 (already in .env.example)

python scripts/setup_local.ps1
```

Or run the full pipeline:

```powershell
python scripts/run_local_pipeline.py
```

---

## Week 2 — Layers 2 & 3 (offline ML)

```powershell
python scripts/generate_sample_data.py
python feature_store/local/feature_engineering.py
python feature_store/local/validate_features.py

$env:FEATURE_STORE_PATH = "data/fraud_features.csv"
$env:MLFLOW_TRACKING_URI = "file:./mlruns"
python ml_training/train.py --generate-xai true
```

**Outputs:**
- `data/fraud_features.csv`
- `data/xai_report.json`
- `data/local/model_metrics.json`
- `data/local/models/rf_model.pkl`
- `mlruns/` experiment runs

---

## Week 3 — Airflow (local orchestration)

```powershell
pip install apache-airflow==2.9.0
$env:AIRFLOW_HOME = "$PWD\orchestration\airflow_home"
$env:INTELLIPIPELINE_ROOT = $PWD
$env:INTELLIPIPELINE_LOCAL = "1"

airflow db migrate
airflow users create --username admin --password admin --role Admin --email admin@local --firstname A --lastname B

# Copy DAGs
New-Item -ItemType Directory -Force -Path "$env:AIRFLOW_HOME\dags"
Copy-Item orchestration\dags\*.py "$env:AIRFLOW_HOME\dags\"

airflow standalone
```

Open http://localhost:8080 → trigger **`intellipipeline_fraud_detection_local`**.

---

## Week 4 — Adaptive monitoring (drift)

```powershell
python serving/drift_detector_local.py
python serving/drift_detector_local.py --simulate-drift   # PSI > 0.25 test
```

Optional local scoring server:

```powershell
python serving/local_score_server.py
# POST http://localhost:5001/score
```

---

## Week 5 — Dashboard

```powershell
# Terminal 1
cd api
$env:INTELLIPIPELINE_LOCAL = "1"
python app.py

# Terminal 2
cd dashboard
npm install
npm run dev
```

http://localhost:5173

---

## Environment variables (local)

```env
INTELLIPIPELINE_LOCAL=1
FEATURE_STORE_PATH=data/fraud_features.csv
MLFLOW_TRACKING_URI=file:./mlruns
# ANTHROPIC_API_KEY=...   # optional for NL query
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `pyarrow` / parquet errors | Use CSV paths; `generate_sample_data.py` falls back to CSV |
| Broken pandas + pyarrow | Use Python **3.11** venv; `pip install pandas numpy` fresh |
| Airflow can't find scripts | Set `INTELLIPIPELINE_ROOT` to repo root |
| Dashboard shows demo data | Run pipeline first; restart API with `INTELLIPIPELINE_LOCAL=1` |
| Low disk space | Skip `pip install apache-airflow` until Week 3 |

---

## What Azure adds later (Week 6+)

- Databricks notebooks → same logic as `feature_store/local/`
- Blob storage → replaces `data/local/`
- Azure ML endpoint → replaces `local_score_server.py`
- Container Apps → replaces `docker compose`

The **local path proves the architecture**; Azure proves you can operate it in production.
