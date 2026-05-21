# serving/retraining_trigger.py
"""CLI wrapper to evaluate drift and optionally trigger Airflow retraining."""

import argparse
import json

from drift_detector import check_drift

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = check_drift()
    if args.dry_run:
        report = {**report, "airflow_triggered": False}
    print(json.dumps(report, indent=2))
