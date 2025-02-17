import os
import io
import time
import random
import pandas as pd
from celery import Celery

# Read your Redis URL from environment (as you had before).
redis_url = os.environ.get("REDIS_URL")
celery = Celery("tasks", broker=redis_url, backend=redis_url)

@celery.task
def process_csv_task(input_key, output_key):
    """
    Downloads 'input_key' from DigitalOcean Spaces, processes it with Selenium,
    and uploads the final CSV to 'output_key' in Spaces.
    """

    # Import what we need from app.py
    # (Avoid circular imports by importing within the function).
    from app import (
        get_spaces_client,
        DO_SPACES_BUCKET,
        create_webdriver,
        search_linkedin_url
    )

    # 1) Connect to Spaces
    s3_client = get_spaces_client()

    # 2) Download the CSV from Spaces into memory
    obj = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=input_key)
    file_data = obj['Body'].read()  # All file bytes in memory

    # 3) Parse CSV with Pandas
    df = pd.read_csv(io.BytesIO(file_data))

    # 4) For each row, do your Selenium scraping
    for i, row in df.iterrows():
        first_name = str(row.get("First Name", ""))
        last_name = str(row.get("Last Name", ""))
        company = str(row.get("Company", ""))

        print(f"Scraping LinkedIn for {first_name} {last_name} @ {company}...")

        driver = create_webdriver()
        linkedin_url = search_linkedin_url(driver, first_name, last_name, company)
        driver.quit()

        df.at[i, "LinkedIn URL"] = linkedin_url

        # Sleep to avoid potential rate limits
        time.sleep(random.uniform(3, 6))

    # 5) Convert processed DataFrame back to CSV
    out_buf = io.StringIO()
    df.to_csv(out_buf, index=False)
    out_buf.seek(0)

    # 6) Upload the processed CSV back to Spaces
    s3_client.put_object(
        Bucket=DO_SPACES_BUCKET,
        Key=output_key,
        Body=out_buf.read().encode('utf-8'),
        ACL='private'  # Keep file private, or 'public-read' if needed
    )

    return f"Processed CSV uploaded to {output_key}"
