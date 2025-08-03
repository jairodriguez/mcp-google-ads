"""
Pytest configuration and fixtures for the Google Ads API tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from typing import Dict, Any
import os
import tempfile
import json

# Import the application
import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app.app)


@pytest.fixture
def sample_customer_id():
    """Provide a sample customer ID for testing."""
    return "1234567890"


@pytest.fixture
def sample_campaign_id():
    """Provide a sample campaign ID for testing."""
    return "customers/1234567890/campaigns/5678"


@pytest.fixture
def sample_campaign_data():
    """Provide sample campaign data for testing."""
    return {
        "customer_id": "1234567890",
        "campaign_name": "Test Campaign",
        "budget_amount": 50.0,
        "geo_targets": [2840],
        "status": "PAUSED"
    }


@pytest.fixture
def sample_ad_group_data():
    """Provide sample ad group data for testing."""
    return {
        "campaign_id": "customers/1234567890/campaigns/5678",
        "ad_group_name": "Test Ad Group",
        "keywords": ["test keyword", "sample keyword"],
        "max_cpc": 1.50,
        "status": "PAUSED"
    }


@pytest.fixture
def mock_google_ads_client():
    """Mock Google Ads client for testing."""
    with patch('app.GoogleAdsClient') as mock_client:
        mock_instance = Mock()
        mock_service = Mock()
        mock_instance.get_service.return_value = mock_service
        mock_client.load_from_storage.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_keyword_ideas_service():
    """Mock KeywordIdeasService for testing."""
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
        yield mock_service


@pytest.fixture
def mock_campaign_service():
    """Mock campaign service for testing."""
    with patch('app.campaign_service') as mock_service:
        mock_campaign = Mock()
        mock_campaign.name = "Test Campaign"
        mock_campaign.status.name = "PAUSED"
        mock_campaign.campaign_budget.amount_micros = 50000000  # $50
        mock_service.get_campaign.return_value = mock_campaign
        yield mock_service


@pytest.fixture
def mock_ad_group_service():
    """Mock ad group service for testing."""
    with patch('app.ad_group_service') as mock_service:
        mock_ad_group = Mock()
        mock_ad_group.name = "Test Ad Group"
        mock_ad_group.status.name = "PAUSED"
        mock_service.get_ad_group.return_value = mock_ad_group
        yield mock_service


@pytest.fixture
def temp_google_ads_config():
    """Create a temporary Google Ads configuration file."""
    config_content = {
        "developer_token": "test_token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "refresh_token": "test_refresh_token",
        "login_customer_id": "1234567890"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        yaml.dump(config_content, f)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    try:
        os.unlink(temp_file)
    except OSError:
        pass


@pytest.fixture
def mock_google_ads_exception():
    """Mock Google Ads API exception for testing error handling."""
    from google.ads.googleads.errors import GoogleAdsException
    
    class MockGoogleAdsException(GoogleAdsException):
        def __init__(self, message="Test Google Ads API error"):
            self.message = message
            self.error_code = "TEST_ERROR"
    
    return MockGoogleAdsException()


@pytest.fixture
def sample_keyword_ideas_response():
    """Provide sample keyword ideas response for testing."""
    return {
        "keywords": [
            {
                "text": "digital marketing agency",
                "avg_monthly_searches": 1000,
                "competition": "HIGH",
                "bid_low_micros": 1500000,
                "bid_high_micros": 3000000
            },
            {
                "text": "seo services",
                "avg_monthly_searches": 800,
                "competition": "MEDIUM",
                "bid_low_micros": 1200000,
                "bid_high_micros": 2500000
            }
        ],
        "status": "success"
    }


@pytest.fixture
def sample_campaign_creation_response():
    """Provide sample campaign creation response for testing."""
    return {
        "success": True,
        "campaign_id": "customers/1234567890/campaigns/5678",
        "message": "Campaign created successfully",
        "request_id": "test-request-id"
    }


@pytest.fixture
def sample_ad_group_creation_response():
    """Provide sample ad group creation response for testing."""
    return {
        "success": True,
        "ad_group_id": "customers/1234567890/adGroups/1234",
        "message": "Ad group created successfully",
        "keywords_added": 2,
        "keywords_failed": 0,
        "failed_keywords": [],
        "total_keywords": 2,
        "request_id": "test-request-id"
    }


@pytest.fixture
def mock_request_id():
    """Mock request ID for testing."""
    return "test-request-id-12345"


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('app.logger') as mock_logger:
        yield mock_logger


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "api: mark test as an API endpoint test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    ) 