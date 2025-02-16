# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set a working directory
WORKDIR /app

# Copy your requirements file
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . /app

# Expose the port your app runs on (App Platform uses PORT env variable)
EXPOSE 8000

# Command to run your Flask app via Gunicorn
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8000}
