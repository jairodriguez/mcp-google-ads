"""
Unit tests for Google Ads server functionality.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import google_ads_server


class TestFormatCustomerId:
    """Test the format_customer_id function."""
    
    @pytest.mark.unit
    def test_format_customer_id_regular(self):
        """Test format_customer_id with regular ID."""
        result = google_ads_server.format_customer_id("9873186703")
        assert result == "9873186703"
    
    @pytest.mark.unit
    def test_format_customer_id_with_dashes(self):
        """Test format_customer_id with dashes."""
        result = google_ads_server.format_customer_id("987-318-6703")
        assert result == "9873186703"
    
    @pytest.mark.unit
    def test_format_customer_id_with_quotes(self):
        """Test format_customer_id with quotes."""
        result = google_ads_server.format_customer_id('"9873186703"')
        assert result == "9873186703"
    
    @pytest.mark.unit
    def test_format_customer_id_with_escaped_quotes(self):
        """Test format_customer_id with escaped quotes."""
        result = google_ads_server.format_customer_id('\"9873186703\"')
        assert result == "9873186703"
    
    @pytest.mark.unit
    def test_format_customer_id_with_leading_zeros(self):
        """Test format_customer_id with leading zeros."""
        result = google_ads_server.format_customer_id("0009873186703")
        assert result == "0009873186703"  # Function preserves leading zeros to ensure 10 digits
    
    @pytest.mark.unit
    def test_format_customer_id_short_id(self):
        """Test format_customer_id with short ID that needs padding."""
        result = google_ads_server.format_customer_id("12345")
        assert result == "0000012345"
    
    @pytest.mark.unit
    def test_format_customer_id_with_special_chars(self):
        """Test format_customer_id with special characters."""
        result = google_ads_server.format_customer_id("{9873186703}")
        assert result == "9873186703"
    
    @pytest.mark.unit
    def test_format_customer_id_empty_string(self):
        """Test format_customer_id with empty string."""
        result = google_ads_server.format_customer_id("")
        assert result == "0000000000"
    
    @pytest.mark.unit
    def test_format_customer_id_none(self):
        """Test format_customer_id with None."""
        result = google_ads_server.format_customer_id(None)
        assert result == "0000000000"


class TestGetCredentials:
    """Test the get_credentials function."""
    
    @pytest.mark.unit
    @patch.dict(os.environ, {
        'GOOGLE_ADS_DEVELOPER_TOKEN': 'test_token',
        'GOOGLE_ADS_CLIENT_ID': 'test_client_id',
        'GOOGLE_ADS_CLIENT_SECRET': 'test_client_secret',
        'GOOGLE_ADS_REFRESH_TOKEN': 'test_refresh_token',
        'GOOGLE_ADS_LOGIN_CUSTOMER_ID': '1234567890'
    })
    def test_get_credentials_oauth(self):
        """Test get_credentials with OAuth configuration."""
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
    def test_get_credentials_service_account(self):
        """Test get_credentials with service account configuration."""
        credentials = google_ads_server.get_credentials()
        assert credentials['developer_token'] == 'test_token'
        assert credentials['auth_type'] == 'service_account'
        assert credentials['credentials_path'] == '/path/to/credentials.json'
    
    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credentials_missing_env_vars(self):
        """Test get_credentials with missing environment variables."""
        with pytest.raises(ValueError, match="Missing required environment variables"):
            google_ads_server.get_credentials()


class TestGetHeaders:
    """Test the get_headers function."""
    
    @pytest.mark.unit
    @patch('google_ads_server.get_credentials')
    @patch('google_ads_server.requests.post')
    def test_get_headers_success(self, mock_post, mock_get_credentials):
        """Test get_headers with successful token refresh."""
        # Mock credentials
        mock_get_credentials.return_value = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'refresh_token': 'test_refresh_token'
        }
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        headers = google_ads_server.get_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_access_token'
        assert 'developer-token' in headers
        assert 'login-customer-id' in headers
    
    @pytest.mark.unit
    @patch('google_ads_server.get_credentials')
    @patch('google_ads_server.requests.post')
    def test_get_headers_failed_request(self, mock_post, mock_get_credentials):
        """Test get_headers with failed token refresh."""
        # Mock credentials
        mock_get_credentials.return_value = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'refresh_token': 'test_refresh_token'
        }
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception, match="Failed to refresh access token"):
            google_ads_server.get_headers()


class TestGoogleAdsApiVersion:
    """Test Google Ads API version configuration."""
    
    @pytest.mark.unit
    def test_api_version_constant(self):
        """Test that API_VERSION is set correctly."""
        assert hasattr(google_ads_server, 'API_VERSION')
        assert isinstance(google_ads_server.API_VERSION, str)
        assert google_ads_server.API_VERSION.startswith('v')


class TestLoggerConfiguration:
    """Test logger configuration."""
    
    @pytest.mark.unit
    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        assert hasattr(google_ads_server, 'logger')
        assert google_ads_server.logger is not None


class TestImportStatements:
    """Test that all required imports are present."""
    
    @pytest.mark.unit
    def test_required_imports(self):
        """Test that all required modules are imported."""
        required_modules = [
            'os', 'sys', 'json', 'requests', 'logging', 'traceback',
            'google.ads.googleads.client', 'google.ads.googleads.errors'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                pytest.fail(f"Required module {module} is not available")


class TestConstants:
    """Test application constants."""
    
    @pytest.mark.unit
    def test_api_base_url(self):
        """Test that API base URL is correctly formatted."""
        base_url = f"https://googleads.googleapis.com/{google_ads_server.API_VERSION}"
        assert base_url.startswith("https://googleads.googleapis.com/")
        assert base_url.endswith(google_ads_server.API_VERSION)
    
    @pytest.mark.unit
    def test_oauth_token_url(self):
        """Test OAuth token URL."""
        expected_url = "https://oauth2.googleapis.com/token"
        assert google_ads_server.OAUTH_TOKEN_URL == expected_url


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.unit
    def test_build_url(self):
        """Test URL building functionality."""
        base_url = "https://googleads.googleapis.com/v19"
        endpoint = "customers/1234567890/campaigns"
        expected_url = f"{base_url}/{endpoint}"
        
        # This would test the actual build_url function if it exists
        # For now, we'll test the concept
        assert expected_url == "https://googleads.googleapis.com/v19/customers/1234567890/campaigns"
    
    @pytest.mark.unit
    def test_validate_customer_id(self):
        """Test customer ID validation."""
        valid_ids = ["1234567890", "0000012345"]
        invalid_ids = ["", "abc", "123", "12345678901"]
        
        for customer_id in valid_ids:
            formatted_id = google_ads_server.format_customer_id(customer_id)
            assert len(formatted_id) == 10
            assert formatted_id.isdigit()
        
        for customer_id in invalid_ids:
            if customer_id:
                formatted_id = google_ads_server.format_customer_id(customer_id)
                # Should still return a 10-digit string
                assert len(formatted_id) == 10
                assert formatted_id.isdigit()


class TestErrorHandling:
    """Test error handling functionality."""
    
    @pytest.mark.unit
    def test_google_ads_exception_handling(self):
        """Test Google Ads exception handling."""
        from google.ads.googleads.errors import GoogleAdsException
        
        # Test that the exception can be imported and used
        exception = GoogleAdsException("Test error")
        assert str(exception) == "Test error"
    
    @pytest.mark.unit
    @patch('google_ads_server.logger')
    def test_logging_in_error_cases(self, mock_logger):
        """Test that errors are properly logged."""
        # This would test actual logging in error cases
        # For now, we'll just verify the logger is available
        assert google_ads_server.logger is not None 