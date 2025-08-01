#!/usr/bin/env python3
"""
Comprehensive test suite for keyword ideas endpoint safeguards.
This ensures the keyword ideas functionality remains isolated and functional
after any changes to campaign creation endpoints.
"""

import pytest
import requests
import json
import time
from typing import Dict, List, Any

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_CUSTOMER_ID = "9197949842"  # Use your test customer ID

class KeywordIdeasSafeguardTests:
    """Test suite for keyword ideas endpoint safeguards"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.test_customer_id = TEST_CUSTOMER_ID
    
    def test_health_check_endpoint(self) -> Dict[str, Any]:
        """Test the keyword ideas health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health/keyword-ideas", timeout=10)
            result = {
                "test_name": "Health Check Endpoint",
                "status": "passed" if response.status_code == 200 else "failed",
                "response_code": response.status_code,
                "response_data": response.json() if response.status_code == 200 else None
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    result["details"] = "Health check passed"
                else:
                    result["status"] = "failed"
                    result["details"] = f"Health check failed: {data.get('error', 'Unknown error')}"
            else:
                result["details"] = f"Health check endpoint returned {response.status_code}"
            
            return result
        except Exception as e:
            return {
                "test_name": "Health Check Endpoint",
                "status": "failed",
                "error": str(e),
                "details": "Exception occurred during health check test"
            }
    
    def test_regression_test_endpoint(self) -> Dict[str, Any]:
        """Test the keyword ideas regression test endpoint"""
        try:
            response = requests.get(f"{self.base_url}/test/keyword-ideas", timeout=10)
            result = {
                "test_name": "Regression Test Endpoint",
                "status": "passed" if response.status_code == 200 else "failed",
                "response_code": response.status_code,
                "response_data": response.json() if response.status_code == 200 else None
            }
            
            if response.status_code == 200:
                data = response.json()
                test_results = data.get("test_results", [])
                all_passed = all(test.get("status") == "passed" for test in test_results)
                
                if all_passed:
                    result["details"] = f"All {len(test_results)} regression tests passed"
                else:
                    result["status"] = "failed"
                    failed_tests = [test for test in test_results if test.get("status") == "failed"]
                    result["details"] = f"{len(failed_tests)} regression tests failed"
                    result["failed_tests"] = failed_tests
            else:
                result["details"] = f"Regression test endpoint returned {response.status_code}"
            
            return result
        except Exception as e:
            return {
                "test_name": "Regression Test Endpoint",
                "status": "failed",
                "error": str(e),
                "details": "Exception occurred during regression test"
            }
    
    def test_keyword_ideas_basic_functionality(self) -> Dict[str, Any]:
        """Test basic keyword ideas functionality"""
        try:
            params = {
                "customer_id": self.test_customer_id,
                "q": ["digital marketing"],
                "geo": "2484",
                "lang": "1003",
                "limit": 5
            }
            
            response = requests.get(f"{self.base_url}/keyword-ideas", params=params, timeout=30)
            result = {
                "test_name": "Basic Keyword Ideas Functionality",
                "status": "passed" if response.status_code == 200 else "failed",
                "response_code": response.status_code,
                "params": params
            }
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    result["details"] = f"Successfully retrieved {len(data)} keyword ideas"
                    result["sample_idea"] = data[0] if data else None
                else:
                    result["status"] = "failed"
                    result["details"] = "No keyword ideas returned or invalid response format"
            else:
                result["details"] = f"Keyword ideas endpoint returned {response.status_code}: {response.text}"
            
            return result
        except Exception as e:
            return {
                "test_name": "Basic Keyword Ideas Functionality",
                "status": "failed",
                "error": str(e),
                "details": "Exception occurred during basic functionality test"
            }
    
    def test_keyword_ideas_parameter_validation(self) -> Dict[str, Any]:
        """Test parameter validation for keyword ideas endpoint"""
        test_cases = [
            {
                "name": "Invalid customer ID",
                "params": {"customer_id": "123", "q": ["test"], "geo": "2484", "lang": "1003"},
                "expected_status": 400
            },
            {
                "name": "Empty keywords",
                "params": {"customer_id": self.test_customer_id, "q": [], "geo": "2484", "lang": "1003"},
                "expected_status": 400
            },
            {
                "name": "Invalid geo target",
                "params": {"customer_id": self.test_customer_id, "q": ["test"], "geo": "invalid", "lang": "1003"},
                "expected_status": 400
            },
            {
                "name": "Invalid language",
                "params": {"customer_id": self.test_customer_id, "q": ["test"], "geo": "2484", "lang": "invalid"},
                "expected_status": 400
            },
            {
                "name": "Invalid limit",
                "params": {"customer_id": self.test_customer_id, "q": ["test"], "geo": "2484", "lang": "1003", "limit": -1},
                "expected_status": 400
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                response = requests.get(f"{self.base_url}/keyword-ideas", params=test_case["params"], timeout=10)
                expected_status = test_case["expected_status"]
                actual_status = response.status_code
                
                result = {
                    "test_name": f"Parameter Validation - {test_case['name']}",
                    "status": "passed" if actual_status == expected_status else "failed",
                    "expected_status": expected_status,
                    "actual_status": actual_status,
                    "params": test_case["params"]
                }
                
                if actual_status == expected_status:
                    result["details"] = f"Correctly returned {actual_status} for invalid parameters"
                else:
                    result["details"] = f"Expected {expected_status} but got {actual_status}"
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "test_name": f"Parameter Validation - {test_case['name']}",
                    "status": "failed",
                    "error": str(e),
                    "details": "Exception occurred during parameter validation test"
                })
        
        return {
            "test_name": "Parameter Validation Tests",
            "status": "passed" if all(r["status"] == "passed" for r in results) else "failed",
            "sub_tests": results,
            "details": f"Ran {len(results)} parameter validation tests"
        }
    
    def test_keyword_ideas_isolation(self) -> Dict[str, Any]:
        """Test that keyword ideas endpoint is isolated from campaign creation changes"""
        try:
            # First, test keyword ideas endpoint
            keyword_params = {
                "customer_id": self.test_customer_id,
                "q": ["test keyword"],
                "geo": "2484",
                "lang": "1003",
                "limit": 3
            }
            
            keyword_response = requests.get(f"{self.base_url}/keyword-ideas", params=keyword_params, timeout=30)
            
            # Then, test that campaign creation endpoint doesn't affect keyword ideas
            # (We'll test with invalid campaign data to avoid actually creating campaigns)
            campaign_data = {
                "customer_id": "1234567890",  # Invalid customer ID
                "campaign_name": "",  # Invalid empty name
                "budget_amount": -10  # Invalid negative budget
            }
            
            campaign_response = requests.post(
                f"{self.base_url}/create-campaign",
                json=campaign_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Test keyword ideas again to ensure it still works
            keyword_response_2 = requests.get(f"{self.base_url}/keyword-ideas", params=keyword_params, timeout=30)
            
            result = {
                "test_name": "Keyword Ideas Isolation",
                "status": "passed",
                "details": "Keyword ideas endpoint remains functional after campaign creation attempts"
            }
            
            # Check that keyword ideas still work after campaign creation attempt
            if keyword_response.status_code == 200 and keyword_response_2.status_code == 200:
                result["details"] = "Keyword ideas endpoint is properly isolated from campaign creation"
            else:
                result["status"] = "failed"
                result["details"] = "Keyword ideas endpoint was affected by campaign creation changes"
                result["keyword_response_1"] = keyword_response.status_code
                result["keyword_response_2"] = keyword_response_2.status_code
            
            return result
        except Exception as e:
            return {
                "test_name": "Keyword Ideas Isolation",
                "status": "failed",
                "error": str(e),
                "details": "Exception occurred during isolation test"
            }
    
    def test_endpoint_response_times(self) -> Dict[str, Any]:
        """Test response times for keyword ideas endpoint"""
        try:
            params = {
                "customer_id": self.test_customer_id,
                "q": ["digital marketing"],
                "geo": "2484",
                "lang": "1003",
                "limit": 5
            }
            
            start_time = time.time()
            response = requests.get(f"{self.base_url}/keyword-ideas", params=params, timeout=30)
            response_time = time.time() - start_time
            
            result = {
                "test_name": "Response Time Test",
                "status": "passed" if response.status_code == 200 and response_time < 30 else "failed",
                "response_time": round(response_time, 2),
                "response_code": response.status_code,
                "details": f"Response time: {response_time:.2f}s"
            }
            
            if response_time > 30:
                result["status"] = "failed"
                result["details"] = f"Response time {response_time:.2f}s exceeds 30 second limit"
            
            return result
        except Exception as e:
            return {
                "test_name": "Response Time Test",
                "status": "failed",
                "error": str(e),
                "details": "Exception occurred during response time test"
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all safeguard tests for keyword ideas endpoint"""
        print("🔍 Running Keyword Ideas Safeguard Tests...")
        print("=" * 60)
        
        tests = [
            self.test_health_check_endpoint,
            self.test_regression_test_endpoint,
            self.test_keyword_ideas_basic_functionality,
            self.test_keyword_ideas_parameter_validation,
            self.test_keyword_ideas_isolation,
            self.test_endpoint_response_times
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                
                # Print test result
                status_icon = "✅" if result["status"] == "passed" else "❌"
                print(f"{status_icon} {result['test_name']}: {result['status']}")
                if result.get("details"):
                    print(f"   Details: {result['details']}")
                
            except Exception as e:
                error_result = {
                    "test_name": test.__name__,
                    "status": "failed",
                    "error": str(e),
                    "details": "Exception occurred during test execution"
                }
                results.append(error_result)
                print(f"❌ {error_result['test_name']}: failed")
                print(f"   Error: {str(e)}")
        
        # Summary
        passed_tests = sum(1 for r in results if r["status"] == "passed")
        total_tests = len(results)
        
        print("=" * 60)
        print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All keyword ideas safeguard tests passed!")
        else:
            print("⚠️  Some tests failed. Review the results above.")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100
            },
            "results": results,
            "timestamp": time.time()
        }

def main():
    """Main function to run the safeguard tests"""
    tester = KeywordIdeasSafeguardTests()
    results = tester.run_all_tests()
    
    # Save results to file
    with open("keyword_ideas_safeguard_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Test results saved to: keyword_ideas_safeguard_test_results.json")
    
    return results["summary"]["success_rate"] == 100

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 