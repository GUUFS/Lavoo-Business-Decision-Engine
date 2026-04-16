# Dockerfile for Alerts Cron Job
# Runs every 2 hours, generates 2 alerts per run

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the alerts cron job
CMD ["python", "cron/alerts.py"]
