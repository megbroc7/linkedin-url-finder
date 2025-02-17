from flask import Flask, request, render_template, send_file, redirect, flash, url_for, jsonify
import os
import random
import shutil
import subprocess
import zipfile  # For unzipping in Python
import boto3
import io
import chromedriver_autoinstaller  # Not used here anymore; kept for reference if needed elsewhere
from werkzeug.utils import secure_filename
from tasks import process_csv_task, celery  # Import the Celery instance as well

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with something more secure in production

# (Optional) Local folders for debugging; main storage is in Spaces.
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

# (Optional) USER_AGENTS removed from here; assumed to be in scraper.py

#############################################
# 1) DigitalOcean Spaces Configuration
#############################################
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_ENDPOINT = f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "my-space-bucket")
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY", "YOUR_SPACES_ACCESS_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET", "YOUR_SPACES_SECRET_KEY")

def get_spaces_client():
    return boto3.client(
        "s3",
        region_name=DO_SPACES_REGION,
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
    )

#############################################
# 2) Utility Functions
#############################################

def allowed_file(filename):
    """Check if the uploaded file is a CSV."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#############################################
# 3) Flask Routes
#############################################

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_data = file.read()

            # Upload the CSV file to Spaces under an "uploads/" prefix.
            spaces_key = f"uploads/{filename}"
            s3_client = get_spaces_client()
            s3_client.put_object(
                Bucket=DO_SPACES_BUCKET,
                Key=spaces_key,
                Body=file_data,
                ACL='private'
            )

            # Define the output key for the processed file.
            output_key = f"outputs/{filename.rsplit('.', 1)[0]}_output.csv"

            try:
                # Offload processing to Celery and get the task id.
                task = process_csv_task.delay(spaces_key, output_key)
            except Exception as e:
                flash(str(e))
                return redirect(request.url)

            flash("File is being processed in the background. Check back later for results.")
            # Redirect to a processing page that will poll for task completion.
            return redirect(url_for('processing', task_id=task.id, output_key=output_key))
    return render_template('index.html')

@app.route('/processing/<task_id>')
def processing(task_id):
    # Retrieve output_key from the query string.
    output_key = request.args.get('output_key')
    # Render processing.html which should have JS polling /status/<task_id>
    return render_template('processing.html', task_id=task_id, output_key=output_key)

@app.route('/status/<task_id>')
def task_status(task_id):
    result = celery.AsyncResult(task_id)
    if result.ready():
        return jsonify({"status": "ready"})
    else:
        return jsonify({"status": "pending"})

@app.route('/complete/<path:filename>')
def processing_complete(filename):
    """
    This route renders the complete.html page where the user can download the file.
    `filename` is the Spaces key for the processed CSV.
    """
    return render_template('complete.html', filename=filename)

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Streams the processed file from Spaces.
    Alternatively, you could generate a presigned URL for direct download.
    """
    s3_client = get_spaces_client()
    try:
        obj = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=filename)
        file_data = obj['Body'].read()
    except Exception as e:
        flash(f"File not found in Spaces: {e}")
        return redirect(url_for('upload_file'))

    return send_file(
        io.BytesIO(file_data),
        as_attachment=True,
        download_name=filename.split('/')[-1]
    )

#############################################
# 4) Running the App
#############################################
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
