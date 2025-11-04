#!/usr/bin/env bash
# Railway Build Script
# This script builds both frontend and backend for Railway deployment

set -e  # Exit on error

echo "🚂 Railway Build Script"
echo "======================="
echo ""

# Step 1: Install Node dependencies
echo "📦 Installing Node.js dependencies..."
npm install
echo "✅ Node dependencies installed"
echo ""

# Step 2: Build React frontend
echo "🎨 Building React frontend..."
npm run build
echo "✅ Frontend built to web/ directory"
echo ""

# Step 3: Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt
echo "✅ Python dependencies installed"
echo ""

# Step 4: Verify build
echo "🔍 Verifying build..."
if [ -d "web" ]; then
    echo "✅ web/ directory exists"
    if [ -f "web/index.html" ]; then
        echo "✅ web/index.html exists"
    else
        echo "❌ web/index.html not found!"
        exit 1
    fi
else
    echo "❌ web/ directory not found!"
    exit 1
fi

echo ""
echo "🎉 Build completed successfully!"
echo "Ready to start with: uvicorn api.main:app --host 0.0.0.0 --port \$PORT"
