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

# Step 2: Build React frontend
echo ""
echo "⚛️  Building React frontend..."
npm run build

# Step 3: Copy build to web directory
echo ""
echo "📁 Copying build to web directory..."
rm -rf web/*
cp -r out/* web/

# Step 4: Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Build complete!"
echo "======================================"
