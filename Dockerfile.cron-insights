# Dockerfile for Insights Cron Job
# Runs every 4 hours, generates 3 insights per run

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the insights cron job
CMD ["python", "cron/insights.py"]
