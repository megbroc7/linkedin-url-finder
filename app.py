from flask import Flask, request, render_template, send_file, redirect, flash, url_for
import os
import time
import random
import shutil
import subprocess
import zipfile  # For unzipping in Python
import boto3
import chromedriver_autoinstaller  # type: ignore
from werkzeug.utils import secure_filename

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Import the Celery task from tasks.py
from tasks import process_csv_task

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with something more secure in production

# (Optional) We won't use local folders since we'll store in Spaces,
# but you can keep them if you want local backups or debugging.
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/94.0.4606.71 Mobile Safari/537.36",
]

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
# 2) Chrome Installation & WebDriver Setup
#############################################

def allowed_file(filename):
    """Check if the uploaded file is a CSV."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def install_chrome():
    """Ensure Chrome is installed, but only install it if it's missing."""
    chrome_path = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    
    if chrome_path:
        print(f"✅ Chrome is already installed at: {chrome_path}")
        return  # Chrome is already installed, so we skip reinstallation

    print("🚀 Installing Chrome...")
    os.makedirs("/tmp/chrome", exist_ok=True)

    # Download the Chrome testing package
    subprocess.run(
        "wget -O /tmp/chrome-linux.zip https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chrome-linux.zip",
        shell=True,
        check=True
    )
    
    # Use Python's zipfile module to extract the downloaded zip file
    with zipfile.ZipFile("/tmp/chrome-linux.zip", "r") as zip_ref:
        zip_ref.extractall("/tmp/chrome/")

    # Set environment variables for Selenium
    os.environ["CHROME_BIN"] = "/tmp/chrome/chrome-linux/chrome"
    os.environ["PATH"] += os.pathsep + "/tmp/chrome/chrome-linux/"

    chromedriver_autoinstaller.install()  # Auto-install ChromeDriver

def create_webdriver():
    """Create a headless WebDriver after ensuring Chrome is installed."""
    install_chrome()

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Hide automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Rotate user-agent
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"user-agent={user_agent}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

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

            # 1) Read the file contents
            file_data = file.read()

            # 2) Choose a key in Spaces
            # e.g. "uploads/" prefix if you like
            spaces_key = f"uploads/{filename}"

            # 3) Upload to Spaces
            s3_client = get_spaces_client()
            s3_client.put_object(
                Bucket=DO_SPACES_BUCKET,
                Key=spaces_key,
                Body=file_data,
                ACL='private'
            )

            # Output key (where processed file might go).
            # Up to you how you handle final output.
            output_key = f"outputs/{filename.rsplit('.', 1)[0]}_output.csv"

            try:
                # Offload the processing to Celery with the Spaces keys
                process_csv_task.delay(spaces_key, output_key)
            except Exception as e:
                flash(str(e))
                return redirect(request.url)

            flash("File is being processed in the background. Check back later for results.")
            # We pass the final output's "filename" or key to the next route for checking
            return redirect(url_for('processing_complete', filename=output_key))

    return render_template('index.html')

@app.route('/complete/<path:filename>')
def processing_complete(filename):
    """
    This route is called after the user is told "Check back later".
    `filename` is actually the Spaces key for the output.
    We'll not check if it's done or not; it's a simple route for demonstration.
    """
    return render_template('complete.html', filename=filename)

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    This route will attempt to stream the processed file from Spaces.
    Alternatively, you can generate a presigned URL and redirect the user to it.
    """
    s3_client = get_spaces_client()

    try:
        obj = s3_client.get_object(Bucket=DO_SPACES_BUCKET, Key=filename)
        file_data = obj['Body'].read()
    except Exception as e:
        flash(f"File not found in Spaces: {e}")
        return redirect(url_for('upload_file'))

    # Return as an attachment
    return send_file(
        io.BytesIO(file_data),
        as_attachment=True,
        download_name=filename.split('/')[-1]
    )

#############################################
# 4) Synchronous Utility (Optional)
#############################################
# If you still have a local process_file or local scraping approach, you can remove it
# or keep it if you also do synchronous code. The final approach is in tasks.py.

#############################################
# 5) Running the App
#############################################

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
