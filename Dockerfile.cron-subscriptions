# Dockerfile for Subscription Expiry Cron Job
# Runs daily at 2 AM UTC to expire old subscriptions

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the subscription expiry cron job
CMD ["python", "cron/subscription_expiry.py"]
