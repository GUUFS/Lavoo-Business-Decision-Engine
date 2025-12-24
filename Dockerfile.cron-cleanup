# Dockerfile for Data Cleanup Cron Job
# Runs daily, deletes data older than 4 months

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the cleanup cron job
CMD ["python", "cron/cleanup.py"]
