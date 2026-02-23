#!/bin/bash

# Run validation script
# Usage: ./run_diagnose.sh <email_or_id>

if [ -z "$1" ]; then
    echo "Usage: ./run_diagnose.sh <email_or_user_id>"
    echo "Example: ./run_diagnose.sh tony@example.com"
    echo "or"
    echo "Example: ./run_diagnose.sh 16"
    exit 1
fi

export PYTHONPATH=$PYTHONPATH:.
python scripts/diagnose_user_data.py "$1"
