#!/bin/bash
# Start script for Railway deployment
# This ensures PORT environment variable is properly used

exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
