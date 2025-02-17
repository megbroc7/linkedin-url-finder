# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install dependencies for Chrome
RUN apt-get update && apt-get install -y wget gnupg --no-install-recommends \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set a working directory
WORKDIR /app

# Copy your requirements file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . /app

# Expose the port your app runs on
EXPOSE 8000

# Command to run your Flask app via Gunicorn
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8000}
