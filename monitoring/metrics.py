# monitoring/metrics.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import os

REQUEST_COUNT = Counter("smartx_requests_total", "Total bot API requests", ["handler"])
TASKS_RUN = Counter("smartx_tasks_run_total", "Total background tasks executed", ["task"])
TASK_DURATION = Histogram("smartx_task_duration_seconds", "Duration of background tasks", ["task"])

PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"

def metrics_endpoint():
    return generate_latest()

# Example usage in web/admin_api:
# from monitoring.metrics import REQUEST_COUNT
# REQUEST_COUNT.labels(handler="broadcast").inc()
