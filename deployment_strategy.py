#!/usr/bin/env python3
"""
Comprehensive deployment strategy for Render deployment.
Handles the 2-5 minute deployment window with health checks, rollback mechanisms,
and deployment verification to ensure continuous service.
"""

import requests
import time
import json
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class RenderDeploymentStrategy:
    """Deployment strategy for Render with health checks and rollback capabilities"""
    
    def __init__(self, base_url: str = "https://mcp-google-ads-vtmp.onrender.com"):
        self.base_url = base_url
        self.deployment_start_time = None
        self.health_check_interval = 30  # seconds
        self.max_deployment_time = 300   # 5 minutes
        self.health_check_timeout = 10   # seconds
        
    def start_deployment_monitoring(self) -> Dict[str, Any]:
        """Start monitoring deployment process"""
        self.deployment_start_time = time.time()
        
        print("🚀 Starting Render deployment monitoring...")
        print(f"📊 Base URL: {self.base_url}")
        print(f"⏱️  Max deployment time: {self.max_deployment_time} seconds")
        print(f"🏥 Health check interval: {self.health_check_interval} seconds")
        print("=" * 60)
        
        return {
            "status": "monitoring_started",
            "base_url": self.base_url,
            "start_time": self.deployment_start_time,
            "max_deployment_time": self.max_deployment_time
        }
    
    def check_endpoint_health(self, endpoint: str) -> Dict[str, Any]:
        """Check health of a specific endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.health_check_timeout)
            
            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "healthy": response.status_code == 200,
                "timestamp": time.time()
            }
        except requests.exceptions.Timeout:
            return {
                "endpoint": endpoint,
                "status_code": None,
                "response_time": None,
                "healthy": False,
                "error": "timeout",
                "timestamp": time.time()
            }
        except requests.exceptions.RequestException as e:
            return {
                "endpoint": endpoint,
                "status_code": None,
                "response_time": None,
                "healthy": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run comprehensive health checks on all critical endpoints"""
        endpoints = [
            "/",
            "/health/keyword-ideas",
            "/test/keyword-ideas",
            "/list-accounts"
        ]
        
        print("🏥 Running health checks...")
        results = {}
        
        for endpoint in endpoints:
            result = self.check_endpoint_health(endpoint)
            results[endpoint] = result
            
            status_icon = "✅" if result["healthy"] else "❌"
            print(f"{status_icon} {endpoint}: {result.get('status_code', 'N/A')} "
                  f"({result.get('response_time', 0):.2f}s)")
        
        all_healthy = all(result["healthy"] for result in results.values())
        
        return {
            "all_healthy": all_healthy,
            "results": results,
            "timestamp": time.time()
        }
    
    def test_keyword_ideas_functionality(self) -> Dict[str, Any]:
        """Test keyword ideas functionality specifically"""
        try:
            # Test with minimal parameters to avoid rate limits
            params = {
                "customer_id": "9197949842",
                "q": ["test"],
                "geo": "2484",
                "lang": "1003",
                "limit": 1
            }
            
            response = requests.get(
                f"{self.base_url}/keyword-ideas",
                params=params,
                timeout=30
            )
            
            return {
                "status": "passed" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "has_data": len(response.json()) > 0 if response.status_code == 200 else False
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "response_time": None
            }
    
    def test_campaign_creation_safely(self) -> Dict[str, Any]:
        """Test campaign creation with invalid data to avoid actual campaign creation"""
        try:
            # Use invalid data to test validation without creating actual campaigns
            test_data = {
                "customer_id": "123",  # Invalid customer ID
                "campaign_name": "",    # Invalid empty name
                "budget_amount": -10    # Invalid negative budget
            }
            
            response = requests.post(
                f"{self.base_url}/create-campaign",
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # We expect a 400 or 422 status for invalid data
            expected_status = response.status_code in [400, 422]
            
            return {
                "status": "passed" if expected_status else "failed",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "validation_working": expected_status
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "response_time": None
            }
    
    def monitor_deployment_progress(self) -> Dict[str, Any]:
        """Monitor deployment progress with periodic health checks"""
        if not self.deployment_start_time:
            return {"error": "Deployment monitoring not started"}
        
        elapsed_time = time.time() - self.deployment_start_time
        
        print(f"⏱️  Deployment elapsed time: {elapsed_time:.1f}s")
        
        # Run health checks
        health_results = self.run_health_checks()
        
        # Test specific functionality
        keyword_test = self.test_keyword_ideas_functionality()
        campaign_test = self.test_campaign_creation_safely()
        
        deployment_status = {
            "elapsed_time": elapsed_time,
            "deployment_complete": elapsed_time >= self.max_deployment_time,
            "health_checks": health_results,
            "keyword_ideas_test": keyword_test,
            "campaign_creation_test": campaign_test,
            "overall_status": "healthy" if (
                health_results["all_healthy"] and 
                keyword_test["status"] == "passed" and
                campaign_test["status"] == "passed"
            ) else "unhealthy"
        }
        
        # Print status
        status_icon = "✅" if deployment_status["overall_status"] == "healthy" else "❌"
        print(f"{status_icon} Overall status: {deployment_status['overall_status']}")
        
        return deployment_status
    
    def generate_deployment_report(self, monitoring_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive deployment report"""
        if not monitoring_results:
            return {"error": "No monitoring results provided"}
        
        # Analyze results
        total_checks = len(monitoring_results)
        healthy_checks = sum(1 for r in monitoring_results if r.get("overall_status") == "healthy")
        deployment_duration = monitoring_results[-1].get("elapsed_time", 0)
        
        # Calculate success rate
        success_rate = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Determine final status
        final_status = "successful" if success_rate >= 80 else "failed"
        
        report = {
            "deployment_status": final_status,
            "success_rate": success_rate,
            "total_health_checks": total_checks,
            "healthy_checks": healthy_checks,
            "deployment_duration_seconds": deployment_duration,
            "monitoring_results": monitoring_results,
            "timestamp": time.time(),
            "recommendations": []
        }
        
        # Add recommendations based on results
        if success_rate < 80:
            report["recommendations"].append("Consider rolling back deployment")
            report["recommendations"].append("Check Render logs for errors")
            report["recommendations"].append("Verify environment variables are set correctly")
        
        if deployment_duration > self.max_deployment_time:
            report["recommendations"].append("Deployment took longer than expected")
        
        return report
    
    def create_rollback_plan(self) -> Dict[str, Any]:
        """Create a rollback plan for failed deployments"""
        rollback_steps = [
            "1. Immediately stop the deployment process",
            "2. Check Render dashboard for deployment status",
            "3. If deployment is still in progress, wait for completion",
            "4. Verify the previous version is still accessible",
            "5. Check environment variables and secrets",
            "6. Review application logs for errors",
            "7. Test critical endpoints manually",
            "8. If issues persist, consider manual rollback via Git"
        ]
        
        return {
            "rollback_plan": rollback_steps,
            "emergency_contacts": [
                "Check Render dashboard: https://dashboard.render.com",
                "Review application logs in Render dashboard",
                "Verify environment variables in Render settings"
            ],
            "critical_endpoints": [
                "/",
                "/health/keyword-ideas",
                "/keyword-ideas",
                "/list-accounts"
            ]
        }

def create_deployment_script() -> str:
    """Create a deployment script for automated deployment"""
    script_content = """#!/bin/bash
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
"""
    return script_content

def create_health_check_script() -> str:
    """Create a health check script for monitoring"""
    script_content = """#!/bin/bash
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
"""
    return script_content

def main():
    """Main function for deployment strategy"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Render Deployment Strategy")
    parser.add_argument("--monitor", action="store_true", help="Start deployment monitoring")
    parser.add_argument("--health-check", action="store_true", help="Run health checks")
    parser.add_argument("--report", action="store_true", help="Generate deployment report")
    parser.add_argument("--rollback-plan", action="store_true", help="Show rollback plan")
    
    args = parser.parse_args()
    
    strategy = RenderDeploymentStrategy()
    
    if args.monitor:
        # Start monitoring
        strategy.start_deployment_monitoring()
        
        # Monitor for the full deployment window
        monitoring_results = []
        while True:
            result = strategy.monitor_deployment_progress()
            monitoring_results.append(result)
            
            if result.get("deployment_complete", False):
                break
            
            time.sleep(strategy.health_check_interval)
        
        # Save monitoring results
        with open("deployment_monitoring_results.json", "w") as f:
            json.dump(monitoring_results, f, indent=2)
        
        print("📊 Monitoring results saved to deployment_monitoring_results.json")
    
    elif args.health_check:
        # Run health checks
        health_results = strategy.run_health_checks()
        keyword_test = strategy.test_keyword_ideas_functionality()
        campaign_test = strategy.test_campaign_creation_safely()
        
        print("📊 Health Check Results:")
        print(f"Overall Health: {'✅' if health_results['all_healthy'] else '❌'}")
        print(f"Keyword Ideas Test: {'✅' if keyword_test['status'] == 'passed' else '❌'}")
        print(f"Campaign Creation Test: {'✅' if campaign_test['status'] == 'passed' else '❌'}")
    
    elif args.report:
        # Generate deployment report
        try:
            with open("deployment_monitoring_results.json", "r") as f:
                monitoring_results = json.load(f)
            
            report = strategy.generate_deployment_report(monitoring_results)
            
            print("📊 Deployment Report:")
            print(f"Status: {report['deployment_status']}")
            print(f"Success Rate: {report['success_rate']:.1f}%")
            print(f"Deployment Duration: {report['deployment_duration_seconds']:.1f}s")
            
            if report.get("recommendations"):
                print("💡 Recommendations:")
                for rec in report["recommendations"]:
                    print(f"  - {rec}")
        
        except FileNotFoundError:
            print("❌ No monitoring results found. Run --monitor first.")
    
    elif args.rollback_plan:
        # Show rollback plan
        plan = strategy.create_rollback_plan()
        
        print("🔄 Rollback Plan:")
        for step in plan["rollback_plan"]:
            print(f"  {step}")
        
        print("\n📞 Emergency Contacts:")
        for contact in plan["emergency_contacts"]:
            print(f"  - {contact}")
    
    else:
        # Create deployment files
        print("📝 Creating deployment files...")
        
        # Create deployment script
        with open("deploy.sh", "w") as f:
            f.write(create_deployment_script())
        os.chmod("deploy.sh", 0o755)
        print("✅ Created deploy.sh")
        
        # Create health check script
        with open("health_check.sh", "w") as f:
            f.write(create_health_check_script())
        os.chmod("health_check.sh", 0o755)
        print("✅ Created health_check.sh")
        
        print("\n🚀 Deployment Strategy Setup Complete!")
        print("Usage:")
        print("  python3 deployment_strategy.py --monitor     # Start monitoring")
        print("  python3 deployment_strategy.py --health-check # Run health checks")
        print("  python3 deployment_strategy.py --report      # Generate report")
        print("  python3 deployment_strategy.py --rollback-plan # Show rollback plan")
        print("  ./deploy.sh                                  # Run deployment script")

if __name__ == "__main__":
    main() 