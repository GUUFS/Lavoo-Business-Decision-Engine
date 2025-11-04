#!/usr/bin/env bash
# Build script for Railway deployment
# This script builds the frontend and prepares it for the backend to serve

set -e  # Exit on error

echo "🔨 Starting Railway build process..."
echo "======================================"

# Step 1: Install Node.js dependencies
echo ""
echo "📦 Installing Node.js dependencies..."
npm install

# Step 2: Build React frontend (now outputs directly to web/)
echo ""
echo "⚛️  Building React frontend..."
npm run build

# Step 3: Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Build complete!"
echo "======================================"
