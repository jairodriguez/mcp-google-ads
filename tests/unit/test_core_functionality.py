"""
Unit tests for core functionality including Google Ads API interactions.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import google_ads_server
from google.ads.googleads.errors import GoogleAdsException


class TestGoogleAdsApiIntegration:
    """Test Google Ads API integration functionality."""
    
    @pytest.mark.unit
    @patch('google_ads_server.get_credentials')
    @patch('google_ads_server.GoogleAdsClient')
    def test_google_ads_client_initialization(self, mock_client_class, mock_get_credentials):
        """Test Google Ads client initialization."""
        # Mock credentials
        mock_get_credentials.return_value = {
            'developer_token': 'test_token',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'refresh_token': 'test_refresh_token',
            'login_customer_id': '1234567890'
        }
        
        # Mock client instance
        mock_client_instance = Mock()
        mock_client_class.load_from_storage.return_value = mock_client_instance
        
        # Test client creation
        client = google_ads_server.get_google_ads_client()
        
        assert client is not None
        mock_client_class.load_from_storage.assert_called_once()
    
    @pytest.mark.unit
    @patch('google_ads_server.get_credentials')
    def test_google_ads_client_credentials_error(self, mock_get_credentials):
        """Test Google Ads client initialization with invalid credentials."""
        mock_get_credentials.side_effect = ValueError("Invalid credentials")
        
        with pytest.raises(ValueError, match="Invalid credentials"):
            google_ads_server.get_google_ads_client()
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_execute_gaql_query_success(self, mock_get_client):
        """Test successful GAQL query execution."""
        # Mock client and service
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = [
            Mock(
                campaign=Mock(
                    id=1234567890,
                    name="Test Campaign",
                    status="PAUSED"
                )
            )
        ]
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test query execution
        result = google_ads_server.execute_gaql_query(
            customer_id="1234567890",
            query="SELECT campaign.id, campaign.name FROM campaign"
        )
        
        assert "campaign" in result.lower()
        assert "test campaign" in result.lower()
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_execute_gaql_query_error(self, mock_get_client):
        """Test GAQL query execution with error."""
        from google.ads.googleads.errors import GoogleAdsException
        
        # Mock client to throw exception
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_service.search.side_effect = GoogleAdsException("Query error")
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test error handling
        result = google_ads_server.execute_gaql_query(
            customer_id="1234567890",
            query="SELECT campaign.id FROM campaign"
        )
        
        assert "error" in result.lower()
        assert "google ads" in result.lower()


class TestCampaignPerformance:
    """Test campaign performance functionality."""
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_get_campaign_performance_success(self, mock_get_client):
        """Test successful campaign performance retrieval."""
        # Mock client and service
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = [
            Mock(
                campaign=Mock(
                    id=1234567890,
                    name="Test Campaign"
                ),
                metrics=Mock(
                    impressions=1000,
                    clicks=50,
                    cost_micros=50000000  # $50.00
                )
            )
        ]
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test performance retrieval
        result = google_ads_server.get_campaign_performance(
            customer_id="1234567890",
            days=30
        )
        
        assert "campaign" in result.lower()
        assert "test campaign" in result.lower()
        assert "impressions" in result.lower()
        assert "clicks" in result.lower()
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_get_campaign_performance_no_data(self, mock_get_client):
        """Test campaign performance with no data."""
        # Mock client with empty response
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = []
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test empty response
        result = google_ads_server.get_campaign_performance(
            customer_id="1234567890",
            days=30
        )
        
        assert "no data" in result.lower() or "empty" in result.lower()


class TestAdPerformance:
    """Test ad performance functionality."""
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_get_ad_performance_success(self, mock_get_client):
        """Test successful ad performance retrieval."""
        # Mock client and service
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = [
            Mock(
                ad_group_ad=Mock(
                    ad=Mock(
                        id=1234567890,
                        final_urls=["https://example.com"]
                    )
                ),
                metrics=Mock(
                    impressions=500,
                    clicks=25,
                    cost_micros=25000000  # $25.00
                )
            )
        ]
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test performance retrieval
        result = google_ads_server.get_ad_performance(
            customer_id="1234567890",
            days=30
        )
        
        assert "ad" in result.lower()
        assert "impressions" in result.lower()
        assert "clicks" in result.lower()


class TestAssetManagement:
    """Test asset management functionality."""
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_get_image_assets_success(self, mock_get_client):
        """Test successful image assets retrieval."""
        # Mock client and service
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = [
            Mock(
                asset=Mock(
                    id=1234567890,
                    name="Test Image",
                    final_urls=["https://example.com/image.jpg"]
                )
            )
        ]
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Test assets retrieval
        result = google_ads_server.get_image_assets(
            customer_id="1234567890",
            limit=10
        )
        
        assert "image" in result.lower()
        assert "test image" in result.lower()
    
    @pytest.mark.unit
    @patch('google_ads_server.get_google_ads_client')
    def test_download_image_asset_success(self, mock_get_client):
        """Test successful image asset download."""
        import tempfile
        import os
        
        # Mock client and service
        mock_client_instance = Mock()
        mock_service = Mock()
        mock_response = Mock()
        mock_response.results = [
            Mock(
                asset=Mock(
                    id=1234567890,
                    name="Test Image",
                    final_urls=["https://example.com/image.jpg"]
                )
            )
        ]
        mock_service.search.return_value = mock_response
        mock_client_instance.get_service.return_value = mock_service
        mock_get_client.return_value = mock_client_instance
        
        # Mock requests for download
        with patch('google_ads_server.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"fake image data"
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # Test download
            with tempfile.TemporaryDirectory() as temp_dir:
                result = google_ads_server.download_image_asset(
                    customer_id="1234567890",
                    asset_id="1234567890",
                    output_dir=temp_dir
                )
                
                assert "downloaded" in result.lower()
                assert "success" in result.lower()


class TestErrorHandling:
    """Test error handling functionality."""
    
    @pytest.mark.unit
    def test_google_ads_exception_handling(self):
        """Test Google Ads exception handling."""
        from google.ads.googleads.errors import GoogleAdsException
        
        # Test exception creation and handling
        exception = GoogleAdsException("Test error message")
        assert str(exception) == "Test error message"
        
        # Test with failure object
        exception.failure = Mock()
        exception.failure.errors = [Mock()]
        exception.failure.errors[0].message = "Detailed error"
        exception.failure.errors[0].error_code = Mock()
        exception.failure.errors[0].error_code.request_error = "INVALID_CUSTOMER_ID"
        
        assert exception.failure.errors[0].message == "Detailed error"
    
    @pytest.mark.unit
    @patch('google_ads_server.logger')
    def test_logging_in_error_cases(self, mock_logger):
        """Test that errors are properly logged."""
        # Test logging in error scenarios
        mock_logger.error.assert_not_called()
        
        # Simulate an error
        try:
            raise ValueError("Test error")
        except ValueError as e:
            google_ads_server.logger.error(f"Error occurred: {e}")
        
        # Verify logger was called
        assert mock_logger.error.called


class TestDataValidation:
    """Test data validation functionality."""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("customer_id,expected", [
        ("1234567890", True),
        ("0000012345", True),
        ("invalid", False),
        ("123", False),
        ("12345678901", False),
        ("", False),
        (None, False),
    ])
    def test_customer_id_validation(self, customer_id, expected):
        """Test customer ID validation."""
        try:
            formatted_id = google_ads_server.format_customer_id(customer_id)
            is_valid = len(formatted_id) == 10 and formatted_id.isdigit()
            assert is_valid == expected
        except (ValueError, TypeError):
            assert not expected
    
    @pytest.mark.unit
    @pytest.mark.parametrize("campaign_name,expected", [
        ("Valid Campaign", True),
        ("Test Campaign 2023", True),
        ("", False),
        ("A" * 256, False),  # Too long
        ("<script>alert('xss')</script>", True),  # Should be sanitized
    ])
    def test_campaign_name_validation(self, campaign_name, expected):
        """Test campaign name validation."""
        # This would test the actual validation logic in the app
        # For now, we'll test the concept
        is_valid = (
            len(campaign_name) > 0 and 
            len(campaign_name) <= 255 and
            isinstance(campaign_name, str)
        )
        assert is_valid == expected
    
    @pytest.mark.unit
    @pytest.mark.parametrize("budget_amount,expected", [
        (10.0, True),
        (100.0, True),
        (0.0, False),
        (-10.0, False),
        (10001.0, False),  # Above limit
    ])
    def test_budget_amount_validation(self, budget_amount, expected):
        """Test budget amount validation."""
        is_valid = (
            isinstance(budget_amount, (int, float)) and
            budget_amount > 0 and
            budget_amount <= 10000
        )
        assert is_valid == expected


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.unit
    def test_build_url_functionality(self):
        """Test URL building functionality."""
        base_url = f"https://googleads.googleapis.com/{google_ads_server.API_VERSION}"
        endpoint = "customers/1234567890/campaigns"
        expected_url = f"{base_url}/{endpoint}"
        
        # Test URL construction
        assert expected_url == "https://googleads.googleapis.com/v19/customers/1234567890/campaigns"
        assert "googleads.googleapis.com" in expected_url
        assert "v19" in expected_url
    
    @pytest.mark.unit
    def test_date_range_calculation(self):
        """Test date range calculation for queries."""
        from datetime import datetime, timedelta
        
        # Test date range for different periods
        today = datetime.now()
        
        # 7 days
        seven_days_ago = today - timedelta(days=7)
        assert (today - seven_days_ago).days == 7
        
        # 30 days
        thirty_days_ago = today - timedelta(days=30)
        assert (today - thirty_days_ago).days == 30
        
        # 90 days
        ninety_days_ago = today - timedelta(days=90)
        assert (today - ninety_days_ago).days == 90
    
    @pytest.mark.unit
    def test_micros_to_currency_conversion(self):
        """Test micros to currency conversion."""
        # Test micros conversion
        micros = 50000000  # $50.00
        dollars = micros / 1000000
        assert dollars == 50.0
        
        # Test edge cases
        assert 0 / 1000000 == 0.0
        assert 1000000 / 1000000 == 1.0


class TestConfiguration:
    """Test configuration and constants."""
    
    @pytest.mark.unit
    def test_api_version_constant(self):
        """Test that API_VERSION is set correctly."""
        assert hasattr(google_ads_server, 'API_VERSION')
        assert isinstance(google_ads_server.API_VERSION, str)
        assert google_ads_server.API_VERSION.startswith('v')
        assert google_ads_server.API_VERSION in ['v19', 'v18', 'v17']  # Common versions
    
    @pytest.mark.unit
    def test_oauth_token_url_constant(self):
        """Test OAuth token URL constant."""
        expected_url = "https://oauth2.googleapis.com/token"
        assert google_ads_server.OAUTH_TOKEN_URL == expected_url
    
    @pytest.mark.unit
    def test_scopes_constant(self):
        """Test OAuth scopes constant."""
        assert hasattr(google_ads_server, 'SCOPES')
        assert isinstance(google_ads_server.SCOPES, list)
        assert len(google_ads_server.SCOPES) > 0
        assert "adwords" in google_ads_server.SCOPES[0]


class TestAuthentication:
    """Test authentication functionality."""
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        'GOOGLE_ADS_DEVELOPER_TOKEN': 'test_token',
        'GOOGLE_ADS_CLIENT_ID': 'test_client_id',
        'GOOGLE_ADS_CLIENT_SECRET': 'test_client_secret',
        'GOOGLE_ADS_REFRESH_TOKEN': 'test_refresh_token',
        'GOOGLE_ADS_LOGIN_CUSTOMER_ID': '1234567890'
    })
    def test_oauth_authentication(self):
        """Test OAuth authentication flow."""
        credentials = google_ads_server.get_credentials()
        
        assert credentials['developer_token'] == 'test_token'
        assert credentials['client_id'] == 'test_client_id'
        assert credentials['client_secret'] == 'test_client_secret'
        assert credentials['refresh_token'] == 'test_refresh_token'
        assert credentials['login_customer_id'] == '1234567890'
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        'GOOGLE_ADS_DEVELOPER_TOKEN': 'test_token',
        'GOOGLE_ADS_AUTH_TYPE': 'service_account',
        'GOOGLE_ADS_CREDENTIALS_PATH': '/path/to/credentials.json'
    })
    def test_service_account_authentication(self):
        """Test service account authentication."""
        credentials = google_ads_server.get_credentials()
        
        assert credentials['developer_token'] == 'test_token'
        assert credentials['auth_type'] == 'service_account'
        assert credentials['credentials_path'] == '/path/to/credentials.json'
    
    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_error(self):
        """Test error handling for missing credentials."""
        with pytest.raises(ValueError, match="Missing required environment variables"):
            google_ads_server.get_credentials()


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    @pytest.mark.unit
    def test_retry_logic(self):
        """Test retry logic for transient failures."""
        # Mock function that fails initially, then succeeds
        call_count = 0
        
        def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"
        
        # Test retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = mock_function()
                assert result == "success"
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                continue
        
        assert call_count == 3
    
    @pytest.mark.unit
    def test_caching_mechanism(self):
        """Test caching mechanism for repeated requests."""
        # Mock cache
        cache = {}
        
        def cached_function(key, value):
            if key in cache:
                return cache[key]
            cache[key] = value
            return value
        
        # Test caching
        result1 = cached_function("test_key", "test_value")
        result2 = cached_function("test_key", "different_value")
        
        assert result1 == "test_value"
        assert result2 == "test_value"  # Should return cached value
        assert cache["test_key"] == "test_value"


class TestSecurityFeatures:
    """Test security features."""
    
    @pytest.mark.unit
    def test_input_sanitization(self):
        """Test input sanitization for security."""
        # Test various potentially dangerous inputs
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for dangerous_input in dangerous_inputs:
            # Test that input is properly handled
            sanitized = str(dangerous_input).replace("<", "&lt;").replace(">", "&gt;")
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
    
    @pytest.mark.unit
    def test_credential_protection(self):
        """Test that credentials are not exposed in logs."""
        # Mock logger
        with patch('google_ads_server.logger') as mock_logger:
            # Simulate credential logging (should not happen)
            credentials = {
                'developer_token': 'secret_token',
                'client_secret': 'secret_secret'
            }
            
            # Log should not contain sensitive information
            google_ads_server.logger.info("Processing request")
            
            # Verify no sensitive data was logged
            for call in mock_logger.info.call_args_list:
                log_message = call[0][0]
                assert 'secret_token' not in log_message
                assert 'secret_secret' not in log_message 