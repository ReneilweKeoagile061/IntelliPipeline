"""
End-to-end local pipeline (no Azure, no Airflow required).

  python scripts/run_local_pipeline.py
  python scripts/run_local_pipeline.py --skip-train
  python scripts/run_local_pipeline.py --drift-simulate
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(cmd: list[str], label: str) -> None:
    print(f"\n{'='*60}\n>> {label}\n{'='*60}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="IntelliPipeline local E2E")
    parser.add_argument("--skip-data", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--drift-simulate", action="store_true", help="Inject drift after pipeline")
    args = parser.parse_args()

    if not args.skip_data:
        run([PY, "scripts/generate_sample_data.py"], "Week 1: Synthetic data")
        run([PY, "feature_store/local/feature_engineering.py"], "Week 2: Feature engineering")
        run([PY, "feature_store/local/validate_features.py"], "Week 2: Feature validation")

    if not args.skip_train:
        env = {
            **os.environ,
            "FEATURE_STORE_PATH": "data/fraud_features.csv",
            "MLFLOW_TRACKING_URI": "file:./mlruns",
            "INTELLIPIPELINE_LOCAL": "1",
        }
        subprocess.run(
            [PY, "ml_training/train.py", "--generate-xai", "true"],
            cwd=ROOT,
            check=True,
            env=env,
        )
        print("\n>> Week 3: Training complete (see mlruns/ and data/xai_report.json)")

    run([PY, "serving/drift_detector_local.py"], "Week 4: Drift detection")

    if args.drift_simulate:
        run([PY, "serving/drift_detector_local.py", "--simulate-drift"], "Week 4: Simulated drift")

    print("\nLocal pipeline finished.")
    print("Next: Week 5 — cd api && python app.py  |  cd dashboard && npm run dev")
    print("       Week 3 — Airflow: see docs/LOCAL_BUILD.md")


if __name__ == "__main__":
    main()
