import os
import io
import time
import random
import pandas as pd
from celery import Celery

# Read your Redis URL from environment variables.
redis_url = os.environ.get("REDIS_URL")
celery = Celery("tasks", broker=redis_url, backend=redis_url)

@celery.task
def process_csv_task(input_key, output_key):
    """
    Downloads the CSV from DigitalOcean Spaces, processes it with Selenium,
    and uploads the final CSV to Spaces.
    Returns the output_key for the processed file.
    """
    # Import dependencies here to avoid circular imports.
    from app import get_spaces_client, DO_SPACES_BUCKET
    from scraper import create_webdriver, search_linkedin_url

    # 1) Connect to Spaces
    s3_client = get_spaces_client()

    # 2) Download the CSV from Spaces into memory.
    obj = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=input_key)
    file_data = obj['Body'].read()

    # 3) Parse CSV using Pandas.
    df = pd.read_csv(io.BytesIO(file_data))

    # 4) For each row, perform Selenium scraping.
    for i, row in df.iterrows():
        first_name = str(row.get("First Name", ""))
        last_name = str(row.get("Last Name", ""))
        company = str(row.get("Company", ""))
        print(f"Scraping LinkedIn for {first_name} {last_name} @ {company}...")
        driver = create_webdriver()
        linkedin_url = search_linkedin_url(driver, first_name, last_name, company)
        driver.quit()
        df.at[i, "LinkedIn URL"] = linkedin_url

        # Sleep to avoid potential rate limits.
        time.sleep(random.uniform(3, 6))

    # 5) Convert the updated DataFrame back to CSV.
    out_buf = io.StringIO()
    df.to_csv(out_buf, index=False)
    out_buf.seek(0)
    csv_content = out_buf.read().encode('utf-8')

    # 6) Upload the processed CSV back to Spaces.
    s3_client.put_object(
        Bucket=DO_SPACES_BUCKET,
        Key=output_key,
        Body=csv_content,
        ACL='private'  # Adjust ACL as needed.
    )

    # Return the output_key so that the client can download the file.
    return output_key
