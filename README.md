# IntelliPipeline

[![Repository](https://img.shields.io/badge/GitHub-ReneilweKeoagile061%2FIntelliPipeline-blue)](https://github.com/ReneilweKeoagile061/IntelliPipeline)

**Intelligent MLOps Data Platform** — fraud detection infrastructure with Policy-as-Code governance, SHAP explainability, PSI drift monitoring, and Claude-powered operations.

**Author:** [Reneilwe Keoagile](https://github.com/ReneilweKeoagile061)

---

## Build locally first (recommended)

We follow **Path B: IntelliPipeline Lite** — end-to-end on your machine in ~4 weeks, Azure only for demos.

| Week | Focus | Command / artifact |
|------|--------|-------------------|
| 1 | Synthetic data | `python scripts/generate_sample_data.py` |
| 2 | Features + training | `python scripts/run_local_pipeline.py` |
| 3 | Airflow orchestration | DAG `intellipipeline_fraud_detection_local` |
| 4 | Drift detector | `python serving/drift_detector_local.py` |
| 5 | Flask + React UI | `api/app.py` + `dashboard` |
| 6+ | Azure port (optional) | See `.env.example` |

**Full guide:** [docs/LOCAL_BUILD.md](docs/LOCAL_BUILD.md)  
**Databricks:** [docs/DATABRICKS.md](docs/DATABRICKS.md) · Week 1 notebook: `notebooks/databricks/IntelliPipeline_Week1_E2E.py`

### Quick start (5 minutes)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
copy .env.example .env
python scripts/run_local_pipeline.py
```

Then start the dashboard:

```powershell
cd api && python app.py          # :5000
cd dashboard && npm install && npm run dev   # :5173
```

---

## Architecture (5 layers)

```
Raw transactions → Airflow DAGs → Feature Store
→ ML training + SHAP XAI → Scoring + PSI drift
→ Auto-retrain → Claude NL dashboard
```

| Layer | Folder | Local entrypoint |
|-------|--------|------------------|
| 1 Orchestration | `orchestration/dags/` | `fraud_pipeline_local.py` |
| 2 Feature store | `feature_store/local/` | `feature_engineering.py`, `validate_features.py` |
| 3 Training | `ml_training/` | `train.py` |
| 4 Serving | `serving/` | `drift_detector_local.py`, `local_score_server.py` |
| 5 Dashboard | `dashboard/` + `api/` | React + Flask RAG |

Databricks notebooks under `feature_store/notebooks/` mirror Layer 2 for **Azure Week 6+**.

---

## Progress

| Area | Status |
|------|--------|
| Project scaffold (all 5 layers) | Done |
| Local pipeline (`run_local_pipeline.py`) | Done |
| Local Airflow DAG | Done |
| Local drift + model artifacts | Done |
| API reads local metrics/drift | Done |
| Azure resources deployed | Not started |
| Production endpoint + Databricks Delta | Not started |

**~50% complete** — local ML loop is buildable today; cloud is optional polish.

---

## What’s left to finish

### Local (weeks 1–5)
- [ ] Run `setup_local.ps1` on Python 3.11 venv
- [ ] Confirm training metrics in `data/local/model_metrics.json`
- [ ] Trigger `intellipipeline_fraud_detection_local` in Airflow UI
- [ ] Test `--simulate-drift` → retrain signal
- [ ] Optional: `ANTHROPIC_API_KEY` for live NL queries

### Azure (week 6+, optional)
- [ ] Resource group + ML workspace + ADLS
- [ ] Run Databricks notebooks against real storage
- [ ] Deploy managed endpoint (`serving/endpoint_config.yml`)
- [ ] Push Airflow image to Container Apps

### Portfolio
- [ ] Architecture diagram + 2-min demo video
- [ ] Blog / LinkedIn post with before/after metrics

---

## Key files

```
scripts/run_local_pipeline.py    # E2E local run
scripts/setup_local.ps1          # Windows bootstrap
feature_store/local/             # Pandas feature pipeline
orchestration/dags/fraud_pipeline_local.py
serving/drift_detector_local.py
requirements-local.txt           # Minimal deps (no Azure SDK required)
```

---

## API (local)

| Endpoint | Description |
|----------|-------------|
| `GET /api/models/health` | Reads `data/local/model_metrics.json` |
| `GET /api/drift` | Reads `data/local/drift_signals/latest_drift.json` |
| `POST /api/query` | Claude RAG (demo mode without API key) |
| `POST /api/explain/{id}` | SHAP + Claude explanation |

---

## Azure vs local

| Capability | Local | Azure |
|------------|-------|-------|
| Feature store | CSV in `data/` | Delta on ADLS |
| Training | MLflow `file:./mlruns` | Azure ML jobs |
| Orchestration | Airflow + subprocess | Container Apps |
| Drift | JSON in `data/local/` | Blob + scheduled job |
| Cost | $0 | ~$200–400 for full demo |

---

## Should you build this?

**Yes** for MLOps / ML Platform / Staff IC roles — demonstrates systems thinking beyond notebook-only projects.

**Path B (this repo)** if you want **zero Azure cost** until interview prep.

---

*IntelliPipeline — build the platform locally, deploy to Azure when it earns its keep.*
