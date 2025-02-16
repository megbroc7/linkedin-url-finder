import os
from celery import Celery

redis_url = os.environ.get("REDIS_URL")
celery = Celery("tasks", broker=redis_url, backend=redis_url)

@celery.task
def process_csv_task(upload_path, output_path):
    from app import process_file
    process_file(upload_path, output_path)
    return "Processing is complete"
