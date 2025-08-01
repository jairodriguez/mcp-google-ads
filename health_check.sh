#!/bin/bash
# Health Check Script for Render Deployment
# Run this script to check the health of deployed endpoints

BASE_URL="https://mcp-google-ads-vtmp.onrender.com"

echo "🏥 Running health checks for ${BASE_URL}..."

# Check root endpoint
echo "Checking root endpoint..."
curl -f -s "${BASE_URL}/" > /dev/null && echo "✅ Root endpoint: OK" || echo "❌ Root endpoint: FAILED"

# Check keyword ideas health
echo "Checking keyword ideas health..."
curl -f -s "${BASE_URL}/health/keyword-ideas" > /dev/null && echo "✅ Keyword ideas health: OK" || echo "❌ Keyword ideas health: FAILED"

# Check list accounts endpoint
echo "Checking list accounts endpoint..."
curl -f -s "${BASE_URL}/list-accounts" > /dev/null && echo "✅ List accounts: OK" || echo "❌ List accounts: FAILED"

echo "🏥 Health checks completed!"
