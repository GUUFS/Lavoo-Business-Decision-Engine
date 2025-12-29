#!/bin/bash

# Security System Restart Script
# This script ensures all database triggers and views are properly reloaded

echo "========================================="
echo "Security System Restart"
echo "========================================="

# Step 1: Stop the backend server
echo ""
echo "Step 1: Stop your backend server (Ctrl+C if running in terminal)"
echo "Press Enter when the server is stopped..."
read

# Step 2: Clear old trigger (optional - only if issues persist)
echo ""
echo "Step 2: Optionally clear the old trigger from database"
echo "Run this SQL command in your database:"
echo ""
echo "DROP TRIGGER IF EXISTS trigger_auto_block ON security_events;"
echo "DROP FUNCTION IF EXISTS auto_block_attacking_ip();"
echo ""
echo "Press Enter when done (or skip if not needed)..."
read

# Step 3: Restart backend
echo ""
echo "Step 3: Start your backend server"
echo "The startup will automatically:"
echo "  - Drop the old security_metrics_summary table"
echo "  - Create all views (recent_security_events, security_metrics_summary, etc.)"
echo "  - Create the auto_block_attacking_ip() function with status field"
echo "  - Create the trigger_auto_block trigger"
echo ""
echo "Start command: python start.py (or uvicorn api.main:app --reload)"
echo ""
echo "Press Enter when server is running..."
read

# Step 4: Verify
echo ""
echo "Step 4: Verification"
echo "========================================="
echo "Run these SQL queries to verify:"
echo ""
echo "1. Check trigger exists:"
echo "   SELECT * FROM pg_trigger WHERE tgname = 'trigger_auto_block';"
echo ""
echo "2. Check function exists:"
echo "   SELECT proname FROM pg_proc WHERE proname = 'auto_block_attacking_ip';"
echo ""
echo "3. Test failed login (5+ times with wrong password)"
echo "4. Check IP blacklist:"
echo "   SELECT * FROM ip_blacklist WHERE is_active=true;"
echo ""
echo "========================================="
echo "Restart Complete!"
echo "========================================="
