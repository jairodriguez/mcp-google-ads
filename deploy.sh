#!/bin/bash
# Render Deployment Script
# This script handles deployment to Render with health checks and rollback

set -e  # Exit on any error

# Configuration
BASE_URL="https://mcp-google-ads-vtmp.onrender.com"
DEPLOYMENT_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=30

echo "🚀 Starting Render deployment..."

# Start deployment monitoring
python3 deployment_strategy.py --monitor &

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete (max ${DEPLOYMENT_TIMEOUT}s)..."
sleep ${DEPLOYMENT_TIMEOUT}

# Run final health checks
echo "🏥 Running final health checks..."
python3 deployment_strategy.py --health-check

# Generate deployment report
echo "📊 Generating deployment report..."
python3 deployment_strategy.py --report

echo "✅ Deployment process completed!"
