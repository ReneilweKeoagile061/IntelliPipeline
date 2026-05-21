"""Shared governance policy constants for IntelliPipeline DAGs."""

GOVERNANCE_POLICIES = {
    "min_data_completeness": 0.95,
    "max_class_imbalance_ratio": 10,
    "required_features": [
        "transaction_amount",
        "merchant_category",
        "customer_age_days",
        "hour_of_day",
        "device_fingerprint",
    ],
    "fairness_threshold": 0.1,
    "data_lineage_required": True,
    "min_model_accuracy": 0.88,
    "max_false_positive_rate": 0.08,
    "green_compute_limit_kwh": 50.0,
}
