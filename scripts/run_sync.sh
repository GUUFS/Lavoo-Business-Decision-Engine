#!/bin/bash

# Script to run the referral count sync SQL queries
# This will connect to your PostgreSQL database and execute the sync queries

# Load database URL from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not found in .env file"
    exit 1
fi

echo "🔄 Syncing referral counts from referrals table..."
echo ""

# Run the SQL file
psql "$DATABASE_URL" -f scripts/sync_referral_counts.sql

echo ""
echo "✅ Sync complete! Please refresh your dashboard to see the updated counts."
