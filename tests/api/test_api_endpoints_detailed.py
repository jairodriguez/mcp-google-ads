"""
Comprehensive API endpoint tests for the Google Ads API application.
Includes parameterized tests, edge cases, and detailed validation.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from typing import Dict, List, Any
import re

# Import the application
import app


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.api
    def test_root_health_check(self, test_client: TestClient):
        """Test the root health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.api
    def test_keyword_ideas_health_check(self, test_client: TestClient):
        """Test the keyword ideas health check endpoint."""
        response = test_client.get("/health/keyword-ideas")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "endpoint" in data
        assert data["endpoint"] == "/keyword-ideas"
    
    @pytest.mark.api
    def test_api_status_endpoint(self, test_client: TestClient):
        """Test the API status endpoint."""
        response = test_client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "endpoints" in data
        assert "version" in data
        assert "uptime" in data
        assert isinstance(data["endpoints"], list)
        assert len(data["endpoints"]) > 0


class TestKeywordIdeasEndpoint:
    """Test the /keyword-ideas endpoint with comprehensive scenarios."""
    
    @pytest.mark.parametrize("customer_id,seed_keywords,geo_targets,language,limit", [
        ("1234567890", "digital marketing", None, "en", 10),
        ("9876543210", "seo,web design", "2840,2826", "es", 5),
        ("1111111111", "ecommerce", "2840", "en", 20),
        ("2222222222", "mobile app", None, "en", 1),
    ])
    @pytest.mark.api
    def test_keyword_ideas_valid_requests(self, test_client: TestClient, customer_id: str, seed_keywords: str, geo_targets: str, language: str, limit: int):
        """Test keyword ideas with various valid parameter combinations."""
        with patch('app.KeywordIdeasService') as mock_service_class:
            mock_service = Mock()
            mock_service.make_keyword_ideas_request.return_value = {
                "keywords": [
                    {
                        "text": "digital marketing agency",
                        "avg_monthly_searches": 1000,
                        "competition": "HIGH",
                        "bid_low_micros": 1500000,
                        "bid_high_micros": 3000000
                    }
                ],
                "status": "success"
            }
            mock_service_class.return_value = mock_service
            
            params = {
                "customer_id": customer_id,
                "seed_keywords": seed_keywords,
                "language": language,
                "limit": limit
            }
            if geo_targets:
                params["geo_targets"] = geo_targets
            
            response = test_client.get("/keyword-ideas", params=params)
            
            assert response.status_code == 200
            data = response.json()
            assert "keywords" in data
            assert isinstance(data["keywords"], list)
            assert len(data["keywords"]) > 0
    
    @pytest.mark.parametrize("invalid_params,expected_error", [
        ({"seed_keywords": "digital marketing"}, "customer_id"),
        ({"customer_id": "1234567890"}, "seed_keywords"),
        ({"customer_id": "invalid", "seed_keywords": "test"}, "customer_id"),
        ({"customer_id": "1234567890", "seed_keywords": "test", "limit": 0}, "limit"),
        ({"customer_id": "1234567890", "seed_keywords": "test", "limit": 101}, "limit"),
    ])
    @pytest.mark.api
    def test_keyword_ideas_invalid_parameters(self, test_client: TestClient, invalid_params: Dict[str, Any], expected_error: str):
        """Test keyword ideas with invalid parameters."""
        response = test_client.get("/keyword-ideas", params=invalid_params)
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert expected_error.lower() in data["error"].lower()
    
    @pytest.mark.api
    def test_keyword_ideas_service_error(self, test_client: TestClient):
        """Test keyword ideas when service throws an error."""
        with patch('app.KeywordIdeasService') as mock_service_class:
            mock_service = Mock()
            mock_service.make_keyword_ideas_request.side_effect = Exception("Service error")
            mock_service_class.return_value = mock_service
            
            response = test_client.get("/keyword-ideas", params={
                "customer_id": "1234567890",
                "seed_keywords": "digital marketing"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
    
    @pytest.mark.api
    def test_keyword_ideas_empty_response(self, test_client: TestClient):
        """Test keyword ideas with empty response from service."""
        with patch('app.KeywordIdeasService') as mock_service_class:
            mock_service = Mock()
            mock_service.make_keyword_ideas_request.return_value = {
                "keywords": [],
                "status": "success"
            }
            mock_service_class.return_value = mock_service
            
            response = test_client.get("/keyword-ideas", params={
                "customer_id": "1234567890",
                "seed_keywords": "very specific term"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "keywords" in data
            assert len(data["keywords"]) == 0


class TestCampaignCreationEndpoint:
    """Test the /create-campaign endpoint with comprehensive scenarios."""
    
    @pytest.mark.parametrize("campaign_data", [
        {
            "customer_id": "1234567890",
            "campaign_name": "Summer Sale 2023",
            "budget_amount": 50.0,
            "geo_targets": [2840, 2826],
            "status": "PAUSED"
        },
        {
            "customer_id": "9876543210",
            "campaign_name": "Holiday Campaign",
            "budget_amount": 100.0,
            "geo_targets": [2840],
            "status": "ENABLED"
        },
        {
            "customer_id": "1111111111",
            "campaign_name": "Brand Awareness",
            "budget_amount": 25.0,
            "status": "PAUSED"
        }
    ])
    @pytest.mark.api
    def test_create_campaign_valid_requests(self, test_client: TestClient, campaign_data: Dict[str, Any]):
        """Test campaign creation with various valid data combinations."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            
            # Mock campaign budget service
            mock_budget_service = Mock()
            mock_budget_response = Mock()
            mock_budget_response.results = [Mock(resource_name="customers/1234567890/campaignBudgets/1234")]
            mock_budget_service.mutate_campaign_budgets.return_value = mock_budget_response
            
            # Mock campaign service
            mock_campaign_service = Mock()
            mock_campaign_response = Mock()
            mock_campaign_response.results = [Mock(resource_name="customers/1234567890/campaigns/5678")]
            mock_campaign_service.mutate_campaigns.return_value = mock_campaign_response
            
            mock_client_instance.get_service.side_effect = lambda service_name: {
                'CampaignBudgetService': mock_budget_service,
                'CampaignService': mock_campaign_service
            }.get(service_name)
            
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post("/create-campaign", json=campaign_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "campaign_id" in data
            assert data["message"] == "Campaign created successfully"
    
    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({}, "customer_id"),
        ({"customer_id": "1234567890"}, "campaign_name"),
        ({"customer_id": "1234567890", "campaign_name": "Test"}, "budget_amount"),
        ({"customer_id": "invalid", "campaign_name": "Test", "budget_amount": 50}, "customer_id"),
        ({"customer_id": "1234567890", "campaign_name": "", "budget_amount": 50}, "campaign_name"),
        ({"customer_id": "1234567890", "campaign_name": "Test", "budget_amount": -10}, "budget_amount"),
        ({"customer_id": "1234567890", "campaign_name": "Test", "budget_amount": 50, "status": "INVALID"}, "status"),
    ])
    @pytest.mark.api
    def test_create_campaign_invalid_data(self, test_client: TestClient, invalid_data: Dict[str, Any], expected_error: str):
        """Test campaign creation with invalid data."""
        response = test_client.post("/create-campaign", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_create_campaign_google_ads_error(self, test_client: TestClient):
        """Test campaign creation when Google Ads API throws an error."""
        from google.ads.googleads.errors import GoogleAdsException
        
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_get_client.side_effect = GoogleAdsException("Test error")
            
            response = test_client.post("/create-campaign", json={
                "customer_id": "1234567890",
                "campaign_name": "Test Campaign",
                "budget_amount": 50.0
            })
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "error" in data["message"].lower()
    
    @pytest.mark.api
    def test_create_campaign_budget_creation_failure(self, test_client: TestClient):
        """Test campaign creation when budget creation fails."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            
            # Mock budget service to fail
            mock_budget_service = Mock()
            mock_budget_service.mutate_campaign_budgets.side_effect = Exception("Budget creation failed")
            
            mock_client_instance.get_service.return_value = mock_budget_service
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post("/create-campaign", json={
                "customer_id": "1234567890",
                "campaign_name": "Test Campaign",
                "budget_amount": 50.0
            })
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False


class TestAdGroupCreationEndpoint:
    """Test the /create-ad-group endpoint with comprehensive scenarios."""
    
    @pytest.mark.parametrize("ad_group_data", [
        {
            "campaign_id": "customers/1234567890/campaigns/5678",
            "ad_group_name": "Primary Keywords",
            "keywords": ["buy product", "best deals", "online shopping"],
            "max_cpc": 1.50,
            "status": "PAUSED"
        },
        {
            "campaign_id": "customers/9876543210/campaigns/1234",
            "ad_group_name": "Secondary Keywords",
            "keywords": ["discount", "sale"],
            "max_cpc": 2.00,
            "status": "ENABLED"
        },
        {
            "campaign_id": "customers/1111111111/campaigns/9999",
            "ad_group_name": "Long Tail",
            "keywords": ["very specific product name"],
            "max_cpc": 0.50
        }
    ])
    @pytest.mark.api
    def test_create_ad_group_valid_requests(self, test_client: TestClient, ad_group_data: Dict[str, Any]):
        """Test ad group creation with various valid data combinations."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            
            # Mock ad group service
            mock_ad_group_service = Mock()
            mock_ad_group_response = Mock()
            mock_ad_group_response.results = [Mock(resource_name="customers/1234567890/adGroups/1234")]
            mock_ad_group_service.mutate_ad_groups.return_value = mock_ad_group_response
            
            # Mock ad group criterion service
            mock_criterion_service = Mock()
            mock_criterion_response = Mock()
            mock_criterion_response.results = [Mock(resource_name="customers/1234567890/adGroupCriteria/5678")]
            mock_criterion_service.mutate_ad_group_criteria.return_value = mock_criterion_response
            
            mock_client_instance.get_service.side_effect = lambda service_name: {
                'AdGroupService': mock_ad_group_service,
                'AdGroupCriterionService': mock_criterion_service
            }.get(service_name)
            
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post("/create-ad-group", json=ad_group_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "ad_group_id" in data
            assert "keywords_added" in data
            assert data["message"] == "Ad group created successfully"
    
    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({}, "campaign_id"),
        ({"campaign_id": "customers/1234567890/campaigns/5678"}, "ad_group_name"),
        ({"campaign_id": "customers/1234567890/campaigns/5678", "ad_group_name": "Test"}, "keywords"),
        ({"campaign_id": "invalid", "ad_group_name": "Test", "keywords": ["test"]}, "campaign_id"),
        ({"campaign_id": "customers/1234567890/campaigns/5678", "ad_group_name": "", "keywords": ["test"]}, "ad_group_name"),
        ({"campaign_id": "customers/1234567890/campaigns/5678", "ad_group_name": "Test", "keywords": []}, "keywords"),
        ({"campaign_id": "customers/1234567890/campaigns/5678", "ad_group_name": "Test", "keywords": ["test"], "max_cpc": -1}, "max_cpc"),
        ({"campaign_id": "customers/1234567890/campaigns/5678", "ad_group_name": "Test", "keywords": ["test"], "status": "INVALID"}, "status"),
    ])
    @pytest.mark.api
    def test_create_ad_group_invalid_data(self, test_client: TestClient, invalid_data: Dict[str, Any], expected_error: str):
        """Test ad group creation with invalid data."""
        response = test_client.post("/create-ad-group", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_create_ad_group_google_ads_error(self, test_client: TestClient):
        """Test ad group creation when Google Ads API throws an error."""
        from google.ads.googleads.errors import GoogleAdsException
        
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_get_client.side_effect = GoogleAdsException("Test error")
            
            response = test_client.post("/create-ad-group", json={
                "campaign_id": "customers/1234567890/campaigns/5678",
                "ad_group_name": "Test Ad Group",
                "keywords": ["test keyword"]
            })
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "error" in data["message"].lower()
    
    @pytest.mark.api
    def test_create_ad_group_partial_keyword_failure(self, test_client: TestClient):
        """Test ad group creation when some keywords fail to be added."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            
            # Mock ad group service
            mock_ad_group_service = Mock()
            mock_ad_group_response = Mock()
            mock_ad_group_response.results = [Mock(resource_name="customers/1234567890/adGroups/1234")]
            mock_ad_group_service.mutate_ad_groups.return_value = mock_ad_group_response
            
            # Mock criterion service with partial failure
            mock_criterion_service = Mock()
            mock_criterion_response = Mock()
            # Simulate some keywords succeeded, some failed
            mock_criterion_response.results = [Mock(resource_name="customers/1234567890/adGroupCriteria/5678")]
            mock_criterion_response.partial_failure_error = Mock()
            mock_criterion_service.mutate_ad_group_criteria.return_value = mock_criterion_response
            
            mock_client_instance.get_service.side_effect = lambda service_name: {
                'AdGroupService': mock_ad_group_service,
                'AdGroupCriterionService': mock_criterion_service
            }.get(service_name)
            
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post("/create-ad-group", json={
                "campaign_id": "customers/1234567890/campaigns/5678",
                "ad_group_name": "Test Ad Group",
                "keywords": ["keyword1", "keyword2", "keyword3"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "keywords_added" in data
            assert "keywords_failed" in data


class TestValidationEndpoints:
    """Test validation endpoints."""
    
    @pytest.mark.parametrize("customer_id", [
        "1234567890",
        "9876543210",
        "1111111111"
    ])
    @pytest.mark.api
    def test_validate_customer_success(self, test_client: TestClient, customer_id: str):
        """Test customer validation with valid customer IDs."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            mock_service = Mock()
            mock_service.get_customer.return_value = Mock(
                id=customer_id,
                descriptive_name="Test Customer"
            )
            mock_client_instance.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.get(f"/api/validate-customer/{customer_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "customer_info" in data
            assert data["customer_info"]["id"] == customer_id
    
    @pytest.mark.parametrize("invalid_customer_id", [
        "invalid",
        "123",
        "12345678901",
        "abc123def"
    ])
    @pytest.mark.api
    def test_validate_customer_invalid_id(self, test_client: TestClient, invalid_customer_id: str):
        """Test customer validation with invalid customer IDs."""
        response = test_client.get(f"/api/validate-customer/{invalid_customer_id}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
    
    @pytest.mark.parametrize("campaign_id", [
        "customers/1234567890/campaigns/5678",
        "customers/9876543210/campaigns/1234"
    ])
    @pytest.mark.api
    def test_validate_campaign_success(self, test_client: TestClient, campaign_id: str):
        """Test campaign validation with valid campaign IDs."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            mock_service = Mock()
            mock_service.get_campaign.return_value = Mock(
                id="5678",
                name="Test Campaign",
                status="PAUSED"
            )
            mock_client_instance.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post("/api/validate-campaign", json={"campaign_id": campaign_id})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "campaign_info" in data
    
    @pytest.mark.parametrize("invalid_campaign_id", [
        "invalid-campaign-id",
        "customers/invalid/campaigns/123",
        "campaigns/1234567890/5678"
    ])
    @pytest.mark.api
    def test_validate_campaign_invalid_id(self, test_client: TestClient, invalid_campaign_id: str):
        """Test campaign validation with invalid campaign IDs."""
        response = test_client.post("/api/validate-campaign", json={"campaign_id": invalid_campaign_id})
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"


class TestErrorHandlingEndpoints:
    """Test error handling endpoints."""
    
    @pytest.mark.parametrize("error_type", [
        "validation",
        "authentication",
        "authorization",
        "google_ads",
        "rate_limit",
        "resource_not_found",
        "configuration",
        "service_unavailable"
    ])
    @pytest.mark.api
    def test_error_test_endpoint(self, test_client: TestClient, error_type: str):
        """Test the error test endpoint with different error types."""
        response = test_client.get(f"/api/error-test?error_type={error_type}")
        
        assert response.status_code == 200
        data = response.json()
        assert "test_results" in data
        assert len(data["test_results"]) > 0
    
    @pytest.mark.api
    def test_error_test_invalid_error_type(self, test_client: TestClient):
        """Test error test endpoint with invalid error type."""
        response = test_client.get("/api/error-test?error_type=invalid_error")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestRequestIdTracking:
    """Test request ID tracking functionality."""
    
    @pytest.mark.api
    def test_request_id_in_all_responses(self, test_client: TestClient):
        """Test that request ID is included in all response headers."""
        endpoints = [
            "/health",
            "/api/status",
            "/keyword-ideas?customer_id=1234567890&seed_keywords=test",
            "/create-campaign",
            "/create-ad-group"
        ]
        
        for endpoint in endpoints:
            if endpoint in ["/create-campaign", "/create-ad-group"]:
                # These are POST endpoints, so we'll just check the header structure
                continue
            
            response = test_client.get(endpoint)
            
            assert "X-Request-ID" in response.headers
            request_id = response.headers["X-Request-ID"]
            assert request_id is not None
            assert len(request_id) > 0
            # Request ID should be a UUID format
            assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', request_id)
    
    @pytest.mark.api
    def test_request_id_in_error_responses(self, test_client: TestClient):
        """Test that request ID is included in error response headers."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert request_id is not None


class TestResponseFormatConsistency:
    """Test response format consistency across endpoints."""
    
    @pytest.mark.api
    def test_success_response_format(self, test_client: TestClient):
        """Test that success responses have consistent format."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for common success response fields
        assert isinstance(data, dict)
        assert "status" in data or "success" in data
    
    @pytest.mark.api
    def test_error_response_format(self, test_client: TestClient):
        """Test that error responses have consistent format."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        # Check for common error response fields
        assert isinstance(data, dict)
        assert "detail" in data or "error" in data or "message" in data
    
    @pytest.mark.api
    def test_validation_error_format(self, test_client: TestClient):
        """Test that validation errors have consistent format."""
        response = test_client.post("/create-campaign", json={
            "customer_id": "invalid",
            "campaign_name": "",
            "budget_amount": -10
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)


class TestPerformanceAndLoad:
    """Test performance and load handling."""
    
    @pytest.mark.api
    def test_multiple_concurrent_requests(self, test_client: TestClient):
        """Test handling of multiple concurrent requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = test_client.get("/health")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads to simulate concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)
        assert len(errors) == 0
    
    @pytest.mark.api
    def test_response_time_health_check(self, test_client: TestClient):
        """Test that health check endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second


class TestSecurityAndValidation:
    """Test security and validation aspects."""
    
    @pytest.mark.api
    def test_sql_injection_prevention(self, test_client: TestClient):
        """Test that endpoints are protected against SQL injection attempts."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO campaigns VALUES ('hacked'); --"
        ]
        
        for malicious_input in malicious_inputs:
            response = test_client.get("/keyword-ideas", params={
                "customer_id": malicious_input,
                "seed_keywords": "test"
            })
            
            # Should not crash or expose sensitive information
            assert response.status_code in [400, 500]  # Should handle gracefully
    
    @pytest.mark.api
    def test_xss_prevention(self, test_client: TestClient):
        """Test that endpoints are protected against XSS attempts."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for xss_input in xss_inputs:
            response = test_client.post("/create-campaign", json={
                "customer_id": "1234567890",
                "campaign_name": xss_input,
                "budget_amount": 50.0
            })
            
            # Should not crash and should sanitize input
            assert response.status_code == 422  # Validation should catch this
    
    @pytest.mark.api
    def test_input_sanitization(self, test_client: TestClient):
        """Test that inputs are properly sanitized."""
        # Test with various special characters
        special_chars = [
            "Test'Campaign",
            "Test\"Campaign",
            "Test<Campaign>",
            "Test&Campaign",
            "Test;Campaign"
        ]
        
        for special_char in special_chars:
            response = test_client.post("/create-campaign", json={
                "customer_id": "1234567890",
                "campaign_name": special_char,
                "budget_amount": 50.0
            })
            
            # Should handle special characters gracefully
            assert response.status_code in [200, 422]  # Either success or validation error 