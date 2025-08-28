# worker/celery_app.py
from celery import Celery
import os
import config
import logging

logger = logging.getLogger("smartx_bot.celery")

BROKER = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL"))
BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER)

celery_app = Celery(
    "smartx_tasks",
    broker=BROKER,
    backend=BACKEND,
)

# recommended: use json
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=100,
    task_soft_time_limit=300,  # per task soft limit
)

# autodiscover tasks from worker.tasks
celery_app.autodiscover_tasks(["worker.tasks"])
