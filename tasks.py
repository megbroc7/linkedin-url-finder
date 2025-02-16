from celery import Celery

# Configure Celery with Redis as the broker and backend
celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery.task
def process_csv_task(upload_path, output_path):
    # Import process_file here to avoid circular imports
    from app import process_file
    process_file(upload_path, output_path)
    return "Processing complete"
