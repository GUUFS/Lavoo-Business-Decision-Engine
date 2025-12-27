#!/usr/bin/env bash
# Script to run Ruff linter and formatter
# Usage: ./lint.sh [check|fix|format|all]

set -e  # Exit on error

echo "🔍 Running Ruff Linter and Formatter..."
echo "========================================"

case "${1:-all}" in
    check)
        echo "📋 Checking code (no fixes)..."
        ruff check . --statistics
        ;;
    fix)
        echo "🔧 Fixing auto-fixable issues..."
        ruff check . --fix
        ;;
    format)
        echo "🎨 Formatting code..."
        ruff format .
        ;;
    all)
        echo "🔧 Step 1: Fixing auto-fixable issues..."
        ruff check . --fix || true
        echo ""
        echo "🎨 Step 2: Formatting code..."
        ruff format .
        echo ""
        echo "📋 Step 3: Final check..."
        ruff check . --statistics || true
        echo ""
        echo "✅ Done!"
        ;;
    *)
        echo "Usage: $0 [check|fix|format|all]"
        echo ""
        echo "Commands:"
        echo "  check   - Check code without making changes"
        echo "  fix     - Auto-fix issues"
        echo "  format  - Format code"
        echo "  all     - Run fix, format, and check (default)"
        exit 1
        ;;
esac
