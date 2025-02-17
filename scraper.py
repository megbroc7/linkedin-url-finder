import os
import time
import random
import shutil
import subprocess
import zipfile
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

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

def install_chrome():
    """Ensure Chrome is installed (if not, download and extract it)."""
    chrome_path = (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if chrome_path:
        print(f"✅ Chrome is already installed at: {chrome_path}")
        return
    print("🚀 Installing Chrome...")
    os.makedirs("/tmp/chrome", exist_ok=True)
    subprocess.run(
        "wget -O /tmp/chrome-linux.zip https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chrome-linux.zip",
        shell=True,
        check=True
    )
    with zipfile.ZipFile("/tmp/chrome-linux.zip", "r") as zip_ref:
        zip_ref.extractall("/tmp/chrome/")
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
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
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
        time.sleep(random.uniform(3, 6))  # Simulate realistic wait time
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
