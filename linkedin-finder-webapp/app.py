from flask import Flask, request, render_template, send_file, redirect, flash, url_for
import os
import pandas as pd
import time
import random
import shutil
import subprocess
import chromedriver_autoinstaller
from werkzeug.utils import secure_filename

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with something more secure in production

# Folders for uploads and outputs (relative paths)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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

    # Install wget if necessary and download Chrome
    subprocess.run("sudo apt update && sudo apt install -y wget", shell=True, check=True)
    subprocess.run(
        "wget -O /tmp/chrome-linux.zip https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chrome-linux.zip",
        shell=True,
        check=True
    )
    subprocess.run(
        "unzip /tmp/chrome-linux.zip -d /tmp/chrome/",
        shell=True,
        check=True
    )

    # Set environment variables for Selenium
    os.environ["CHROME_BIN"] = "/tmp/chrome/chrome-linux/chrome"
    os.environ["PATH"] += os.pathsep + "/tmp/chrome/chrome-linux/"

    chromedriver_autoinstaller.install()  # Auto-install ChromeDriver

def create_webdriver():
    """Ensure Chrome is installed, then create a memory-optimized WebDriver."""
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

def search_linkedin_url(driver, first_name, last_name, company):
    """Scrapes Google for a LinkedIn profile based on name & company."""
    query = f"{first_name} {last_name} {company} site:linkedin.com"
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

    try:
        driver.get(search_url)
        time.sleep(random.uniform(3, 6))  # Wait like a real user

        # Simulate scrolling
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
        time.sleep(random.uniform(1, 2))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 2))

        links = driver.find_elements(By.CSS_SELECTOR, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and "linkedin.com/in/" in href:
                return href
        return "Not found"
    except Exception as e:
        return f"Error: {str(e)}"

def process_file(input_path, output_path):
    """Reads the CSV, scrapes LinkedIn URLs, writes to a new CSV."""
    df = pd.read_csv(input_path)
<<<<<<< HEAD
=======

    required = {"First Name", "Last Name", "Company"}
    if not required.issubset(df.columns):
        raise ValueError("Input CSV must have columns: First Name, Last Name, Company")

    if len(df) > 100:
        raise ValueError("You can only process up to 100 searches at once.")

    df["LinkedIn URL"] = ""

    for i, row in df.iterrows():
        first_name = str(row["First Name"])
        last_name = str(row["Last Name"])
        company = str(row["Company"])

        print(f"Searching LinkedIn for {first_name} {last_name} @ {company}...")
        driver = create_webdriver()
        linkedin_url = search_linkedin_url(driver, first_name, last_name, company)
        driver.quit()

        df.at[i, "LinkedIn URL"] = linkedin_url

        time.sleep(random.uniform(5, 10))

    df.to_csv(output_path, index=False)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)
>>>>>>> 091560c (Updated Gunicorn settings)

    # Validate columns
    required = {"First Name", "Last Name", "Company"}
    if not required.issubset(df.columns):
        raise ValueError("Input CSV must have columns: First Name, Last Name, Company")

    if len(df) > 100:
        raise ValueError("You can only process up to 100 searches at once. Please reduce your file size.")

    df["LinkedIn URL"] = ""

    for i, row in df.iterrows():
        first_name = str(row["First Name"])
        last_name = str(row["Last Name"])
        company = str(row["Company"])
        
        print(f"Searching LinkedIn for {first_name} {last_name} @ {company}...")
        driver = create_webdriver()
        linkedin_url = search_linkedin_url(driver, first_name, last_name, company)
        driver.quit()

        df.at[i, "LinkedIn URL"] = linkedin_url
        
        # Pause to avoid rate limits
        time.sleep(random.uniform(5, 10))

    df.to_csv(output_path, index=False)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
