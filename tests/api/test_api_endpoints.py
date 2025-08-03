"""
API endpoint tests for the FastAPI application.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from typing import Dict, List, Any

# Import the application
import app


class TestKeywordIdeasEndpoint:
    """Test the /keyword-ideas endpoint."""
    
    @pytest.mark.api
    def test_keyword_ideas_success(self, test_client: TestClient, mock_google_ads_client, sample_customer_id: str):
        """Test successful keyword ideas request."""
        # Mock the Google Ads client response
        mock_response = Mock()
        mock_response.results = [
            Mock(
                keyword_idea=Mock(
                    text="digital marketing agency",
                    keyword_annotations=Mock(
                        search_volume=1000,
                        competition=0.75
                    )
                )
            ),
            Mock(
                keyword_idea=Mock(
                    text="seo services",
                    keyword_annotations=Mock(
                        search_volume=800,
                        competition=0.50
                    )
                )
            )
        ]
        
        with patch('app.get_credentials') as mock_get_credentials, patch('app.get_headers') as mock_get_headers, patch('app.requests.post') as mock_post:
            mock_credentials = Mock()
            mock_headers = {"Authorization": "Bearer test_token"}
            mock_get_credentials.return_value = mock_credentials
            mock_get_headers.return_value = mock_headers
            
            # Mock the API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "keywordIdea": {
                            "text": "digital marketing agency",
                            "keywordAnnotations": {
                                "searchVolume": 1000,
                                "competition": "HIGH"
                            }
                        }
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            response = test_client.get(
                "/keyword-ideas",
                params={
                    "customer_id": sample_customer_id,
                    "seed_keywords": "digital marketing",
                    "geo_targets": "2840",
                    "language": "en",
                    "limit": 5
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
        assert len(data["keywords"]) > 0
        assert data["status"] == "success"
    
    @pytest.mark.api
    def test_keyword_ideas_missing_customer_id(self, test_client: TestClient):
        """Test keyword ideas with missing customer ID."""
        response = test_client.get(
            "/keyword-ideas",
            params={
                "seed_keywords": "digital marketing",
                "geo_targets": "2840",
                "language": "en",
                "limit": 5
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_keyword_ideas_invalid_customer_id(self, test_client: TestClient):
        """Test keyword ideas with invalid customer ID."""
        response = test_client.get(
            "/keyword-ideas",
            params={
                "customer_id": "invalid",
                "seed_keywords": "digital marketing",
                "geo_targets": "2840",
                "language": "en",
                "limit": 5
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_keyword_ideas_missing_keywords(self, test_client: TestClient, sample_customer_id: str):
        """Test keyword ideas with missing keywords."""
        response = test_client.get(
            "/keyword-ideas",
            params={
                "customer_id": sample_customer_id,
                "geo_targets": "2840",
                "language": "en",
                "limit": 5
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    @patch('app.requests.post')
    def test_keyword_ideas_google_ads_error(self, mock_post, test_client: TestClient, sample_customer_id: str):
        """Test keyword ideas with Google Ads API error."""
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        response = test_client.get(
            "/keyword-ideas",
            params={
                "customer_id": sample_customer_id,
                "seed_keywords": "digital marketing",
                "geo_targets": "2840",
                "language": "en",
                "limit": 5
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


class TestCampaignCreationEndpoint:
    """Test the /create-campaign endpoint."""
    
    @pytest.mark.api
    def test_create_campaign_success(self, test_client: TestClient, sample_campaign_data: Dict[str, Any]):
        """Test successful campaign creation."""
        with patch('app.GoogleAdsClient') as mock_google_ads_client:
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
            
            mock_google_ads_client.load_from_storage.return_value = mock_client_instance
            
            response = test_client.post(
                "/create-campaign",
                json=sample_campaign_data
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "campaign_id" in data
    
    @pytest.mark.api
    def test_create_campaign_missing_required_fields(self, test_client: TestClient):
        """Test campaign creation with missing required fields."""
        response = test_client.post(
            "/create-campaign",
            json={
                "customer_id": "1234567890",
                "campaign_name": "Test Campaign"
                # Missing budget_amount
            }
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_create_campaign_invalid_budget(self, test_client: TestClient):
        """Test campaign creation with invalid budget."""
        response = test_client.post(
            "/create-campaign",
            json={
                "customer_id": "1234567890",
                "campaign_name": "Test Campaign",
                "budget_amount": -10.0,  # Invalid negative budget
                "status": "PAUSED"
            }
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    @patch('app.GoogleAdsClient')
    def test_create_campaign_google_ads_error(self, mock_google_ads_client, test_client: TestClient, sample_campaign_data: Dict[str, Any]):
        """Test campaign creation with Google Ads API error."""
        from google.ads.googleads.errors import GoogleAdsException
        
        # Mock Google Ads exception
        mock_google_ads_client.load_from_storage.side_effect = GoogleAdsException("Test error")
        
        response = test_client.post(
            "/create-campaign",
            json=sample_campaign_data
        )
        
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "google ads" in data["message"].lower()


class TestAdGroupCreationEndpoint:
    """Test the /create-ad-group endpoint."""
    
    @pytest.mark.api
    def test_create_ad_group_success(self, test_client: TestClient, sample_ad_group_data: Dict[str, Any]):
        """Test successful ad group creation."""
        with patch('app.GoogleAdsClient') as mock_google_ads_client:
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
            
            mock_google_ads_client.load_from_storage.return_value = mock_client_instance
            
            response = test_client.post(
                "/create-ad-group",
                json=sample_ad_group_data
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "ad_group_id" in data
        assert "keywords_added" in data
    
    @pytest.mark.api
    def test_create_ad_group_missing_required_fields(self, test_client: TestClient):
        """Test ad group creation with missing required fields."""
        response = test_client.post(
            "/create-ad-group",
            json={
                "campaign_id": "customers/1234567890/campaigns/9876543210",
                "ad_group_name": "Test Ad Group"
                # Missing keywords
            }
        )
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_create_ad_group_invalid_campaign_id(self, test_client: TestClient):
        """Test ad group creation with invalid campaign ID."""
        response = test_client.post(
            "/create-ad-group",
            json={
                "campaign_id": "invalid-campaign-id",
                "ad_group_name": "Test Ad Group",
                "keywords": ["test keyword"],
                "max_cpc": 1.50
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "campaign" in data["message"].lower()
    
    @pytest.mark.api
    @patch('app.GoogleAdsClient')
    def test_create_ad_group_google_ads_error(self, mock_google_ads_client, test_client: TestClient, sample_ad_group_data: Dict[str, Any]):
        """Test ad group creation with Google Ads API error."""
        from google.ads.googleads.errors import GoogleAdsException
        
        # Mock Google Ads exception
        mock_google_ads_client.load_from_storage.side_effect = GoogleAdsException("Test error")
        
        response = test_client.post(
            "/create-ad-group",
            json=sample_ad_group_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "google ads" in data["message"].lower()


class TestHealthCheckEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.api
    def test_health_check(self, test_client: TestClient):
        """Test the basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    @pytest.mark.api
    def test_keyword_ideas_health_check(self, test_client: TestClient):
        """Test the keyword ideas health check endpoint."""
        response = test_client.get("/health/keyword-ideas")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @pytest.mark.api
    def test_api_status(self, test_client: TestClient):
        """Test the API status endpoint."""
        response = test_client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "endpoints" in data
        assert "version" in data


class TestValidationEndpoints:
    """Test validation endpoints."""
    
    @pytest.mark.api
    def test_validate_customer_success(self, test_client: TestClient, sample_customer_id: str):
        """Test customer validation with valid customer ID."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            mock_service = Mock()
            mock_service.get_customer.return_value = Mock(
                id=sample_customer_id,
                descriptive_name="Test Customer"
            )
            mock_client_instance.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.get(f"/api/validate-customer/{sample_customer_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "customer_info" in data
    
    @pytest.mark.api
    def test_validate_customer_invalid_id(self, test_client: TestClient):
        """Test customer validation with invalid customer ID."""
        response = test_client.get("/api/validate-customer/invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
    
    @pytest.mark.api
    def test_validate_campaign_success(self, test_client: TestClient, sample_campaign_id: str):
        """Test campaign validation with valid campaign ID."""
        with patch('app.get_google_ads_client') as mock_get_client:
            mock_client_instance = Mock()
            mock_service = Mock()
            mock_service.get_campaign.return_value = Mock(
                id="9876543210",
                name="Test Campaign",
                status="PAUSED"
            )
            mock_client_instance.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client_instance
            
            response = test_client.post(
                "/api/validate-campaign",
                json={"campaign_id": sample_campaign_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "campaign_info" in data
    
    @pytest.mark.api
    def test_validate_campaign_invalid_id(self, test_client: TestClient):
        """Test campaign validation with invalid campaign ID."""
        response = test_client.post(
            "/api/validate-campaign",
            json={"campaign_id": "invalid-campaign-id"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    @pytest.mark.api
    def test_error_test_endpoint(self, test_client: TestClient):
        """Test the error test endpoint."""
        response = test_client.get("/api/error-test")
        
        assert response.status_code == 200
        data = response.json()
        assert "test_results" in data
        assert len(data["test_results"]) > 0
    
    @pytest.mark.api
    def test_404_error(self, test_client: TestClient):
        """Test 404 error handling."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.api
    def test_validation_error(self, test_client: TestClient):
        """Test validation error handling."""
        response = test_client.post(
            "/create-campaign",
            json={
                "customer_id": "invalid",
                "campaign_name": "",  # Invalid empty name
                "budget_amount": -1,  # Invalid negative budget
                "status": "INVALID_STATUS"  # Invalid status
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestRequestIdTracking:
    """Test request ID tracking functionality."""
    
    @pytest.mark.api
    def test_request_id_in_response(self, test_client: TestClient):
        """Test that request ID is included in response headers."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
    
    @pytest.mark.api
    def test_request_id_in_error_response(self, test_client: TestClient):
        """Test that request ID is included in error response headers."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None


class TestResponseFormat:
    """Test response format consistency."""
    
    @pytest.mark.api
    def test_success_response_format(self, test_client: TestClient):
        """Test that success responses have consistent format."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for common success response fields
        assert isinstance(data, dict)
        assert "status" in data or "message" in data
    
    @pytest.mark.api
    def test_error_response_format(self, test_client: TestClient):
        """Test that error responses have consistent format."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        # Check for common error response fields
        assert isinstance(data, dict)
        assert "detail" in data or "message" in data 