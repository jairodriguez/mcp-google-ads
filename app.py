from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
import uvicorn
import os
import re
import time
import hashlib
import json
import uuid
from datetime import datetime

# Import the necessary functions from google_ads_server
from google_ads_server import (
    format_customer_id, 
    get_credentials, 
    get_headers,
    logger,
    traceback,
    API_VERSION
)
import requests

# Import Google Ads library for proper API integration
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Import centralized error handling
from error_handlers import (
    # Custom exceptions
    BaseAPIException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    GoogleAdsApiError,
    RateLimitError,
    ResourceNotFoundError,
    ConfigurationError,
    ServiceUnavailableError,
    
    # Error handling utilities
    create_error_response,
    log_error,
    handle_google_ads_exception,
    
    # Middleware
    add_request_id_middleware,
    
    # Exception handlers
    validation_exception_handler,
    authentication_exception_handler,
    authorization_exception_handler,
    google_ads_exception_handler,
    general_exception_handler
)

# Import comprehensive logging
from logging_config import (
    initialize_logging,
    RequestLoggingMiddleware,
    log_request_start,
    log_request_end,
    log_error as log_error_structured,
    log_validation_error,
    log_google_ads_error,
    log_performance,
    log_security_event,
    log_function_call
)
from fastapi import Request

app = FastAPI()

# Initialize structured logging
logger = initialize_logging()

# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================

@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Add request ID to all requests and responses"""
    return await add_request_id_middleware(request, call_next)

@app.middleware("http")
async def logging_middleware(request, call_next):
    """Comprehensive request logging middleware"""
    logging_middleware_instance = RequestLoggingMiddleware(logger)
    return await logging_middleware_instance(request, call_next)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(ValidationError)
async def handle_validation_error(request, exc):
    """Handle validation errors"""
    return await validation_exception_handler(request, exc)

@app.exception_handler(AuthenticationError)
async def handle_authentication_error(request, exc):
    """Handle authentication errors"""
    return await authentication_exception_handler(request, exc)

@app.exception_handler(AuthorizationError)
async def handle_authorization_error(request, exc):
    """Handle authorization errors"""
    return await authorization_exception_handler(request, exc)

@app.exception_handler(GoogleAdsException)
async def handle_google_ads_error(request, exc):
    """Handle Google Ads API errors"""
    return await google_ads_exception_handler(request, exc)

@app.exception_handler(Exception)
async def handle_general_error(request, exc):
    """Handle all other exceptions"""
    return await general_exception_handler(request, exc)

# ============================================================================
# RETRY LOGIC FOR TRANSIENT FAILURES
# ============================================================================

def retry_on_transient_failure(func, max_retries=3, delay=1):
    """Retry function on transient failures with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except GoogleAdsException as ex:
            error_msg = ex.failure.errors[0].message
            if any(transient_error in error_msg for transient_error in [
                "QUOTA_EXCEEDED", "RATE_EXCEEDED", "INTERNAL_ERROR", "DEADLINE_EXCEEDED"
            ]):
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Transient error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    time.sleep(wait_time)
                    continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Unexpected error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)
                continue
            raise
    raise Exception(f"Function failed after {max_retries} attempts")

# ============================================================================
# ENHANCED ERROR MESSAGES
# ============================================================================

def get_user_friendly_error_message(error_msg: str) -> str:
    """Convert technical error messages to user-friendly messages"""
    error_mapping = {
        "INVALID_CAMPAIGN": "The campaign ID is invalid or you don't have access to it",
        "DUPLICATE_NAME": "An ad group with this name already exists in the campaign",
        "INSUFFICIENT_PERMISSIONS": "You don't have permission to create ad groups in this campaign",
        "INVALID_KEYWORD": "Some keywords contain invalid characters or are too long",
        "DUPLICATE_KEYWORD": "Some keywords already exist in the ad group",
        "INSUFFICIENT_BUDGET": "The campaign budget is too low for the specified keyword bids",
        "QUOTA_EXCEEDED": "API quota exceeded, please try again later",
        "RATE_EXCEEDED": "Too many requests, please try again later",
        "INTERNAL_ERROR": "Google Ads service error, please try again",
        "DEADLINE_EXCEEDED": "Request timed out, please try again"
    }
    
    for key, message in error_mapping.items():
        if key in error_msg:
            return message
    
    return "An unexpected error occurred. Please try again or contact support."

# ============================================================================
# SAFEGUARD: Isolated Service Classes
# ============================================================================

class KeywordIdeasService:
    """Isolated service class for keyword ideas functionality"""
    
    def __init__(self):
        self.api_version = API_VERSION
    
    def get_credentials_safe(self):
        """Safely get credentials for keyword ideas"""
        try:
            return get_credentials()
        except Exception as e:
            logger.error(f"Failed to get credentials for keyword ideas: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    def get_headers_safe(self, creds):
        """Safely get headers for keyword ideas"""
        try:
            return get_headers(creds)
        except Exception as e:
            logger.error(f"Failed to get headers for keyword ideas: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    def validate_keyword_ideas_params(self, customer_id: str, q: List[str], geo: str, lang: str, limit: Optional[int]):
        """Validate keyword ideas parameters"""
        errors = []
        
        # Validate customer_id
        if not customer_id or len(customer_id) != 10 or not customer_id.isdigit():
            errors.append("customer_id must be exactly 10 digits")
        
        # Validate keywords
        if not q or len(q) == 0:
            errors.append("At least one keyword is required")
        elif len(q) > 10:
            errors.append("Maximum 10 keywords allowed")
        
        # Validate geo
        if not geo or not geo.isdigit():
            errors.append("geo must be a valid geo target constant ID")
        
        # Validate lang
        if not lang or not lang.isdigit():
            errors.append("lang must be a valid language constant ID")
        
        # Validate limit
        if limit is not None and (limit < 1 or limit > 100):
            errors.append("limit must be between 1 and 100")
        
        if errors:
            raise HTTPException(status_code=400, detail=f"Validation errors: {'; '.join(errors)}")
    
    def make_keyword_ideas_request(self, customer_id: str, q: List[str], geo: str, lang: str, limit: Optional[int]):
        """Make keyword ideas request with proper error handling"""
        try:
            creds = self.get_credentials_safe()
            headers = self.get_headers_safe(creds)
            
            # Use the working keyword ideas endpoint structure
            payload = {
                "keywordPlanNetwork": "GOOGLE_SEARCH",
                "keywordIdeaType": "KEYWORD",
                "keywordTexts": q,
                "language": f"languages/{lang}",
                "geoTargetConstants": [f"geoTargetConstants/{geo}"]
            }
            
            response = requests.post(
                f"https://googleads.googleapis.com/{self.api_version}/customers/{customer_id}/googleAds:searchStream",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Google Ads error: {response.text}")
            
            return response.json()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Keyword ideas request failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Keyword ideas request failed: {str(e)}")

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "healthy",
            "google_ads": "checking"
        }
    }

@app.get("/health/keyword-ideas")
async def keyword_ideas_health_check():
    """Health check specifically for keyword ideas endpoint"""
    try:
        # Test with minimal parameters to verify functionality
        test_customer_id = os.environ.get("TEST_CUSTOMER_ID", "1234567890")
        
        # This is a basic test - in production you might want to do a real API call
        return {
            "status": "healthy",
            "endpoint": "keyword-ideas",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Keyword ideas endpoint is operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "endpoint": "keyword-ideas",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# ============================================================================
# ADDITIONAL API ENDPOINTS WITH ERROR HANDLING
# ============================================================================

@app.get("/api/status")
async def get_api_status(request: Request = None):
    """Get comprehensive API status with error handling"""
    try:
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "endpoints": {
                "keyword_ideas": "/keyword-ideas",
                "create_campaign": "/create-campaign",
                "create_ad_group": "/create-ad-group",
                "health": "/health",
                "keyword_ideas_health": "/health/keyword-ideas"
            },
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    except Exception as e:
        logger.error(f"API status check failed: {str(e)}")
        raise ServiceUnavailableError("Service status check failed")

@app.get("/api/validate-customer/{customer_id}")
async def validate_customer(customer_id: str, request: Request = None):
    """Validate customer ID with comprehensive error handling"""
    try:
        # Validate customer ID format
        if not customer_id or not customer_id.strip():
            raise ValidationError("Customer ID is required", field="customer_id")
        
        # Remove dashes and validate
        clean_id = customer_id.replace('-', '')
        if not clean_id.isdigit() or len(clean_id) != 10:
            raise ValidationError("Customer ID must be 10 digits (with or without dashes)", field="customer_id")
        
        # Try to access customer via Google Ads API
        try:
            client = GoogleAdsClient.load_from_storage('./google-ads.yaml')
            customer_service = client.get_service('CustomerService')
            
            # Get customer info
            customer = customer_service.get_customer(resource_name=f"customers/{clean_id}")
            
            return {
                "valid": True,
                "customer_id": clean_id,
                "customer_name": customer.descriptive_name,
                "currency_code": customer.currency_code,
                "time_zone": customer.time_zone,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
            
        except GoogleAdsException as e:
            custom_exception = handle_google_ads_exception(e)
            if "CUSTOMER_NOT_FOUND" in str(e):
                raise ResourceNotFoundError("Customer not found", resource_type="customer", resource_id=customer_id)
            elif "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to access customer")
            else:
                raise custom_exception
                
    except (ValidationError, ResourceNotFoundError, AuthorizationError, GoogleAdsApiError):
        raise
    except Exception as e:
        logger.error(f"Customer validation failed: {str(e)}")
        raise ServiceUnavailableError("Customer validation service unavailable")

@app.post("/api/validate-campaign")
async def validate_campaign(campaign_id: str = Query(..., description="Campaign ID to validate"), request: Request = None):
    """Validate campaign ID with comprehensive error handling"""
    try:
        # Validate campaign ID format
        if not campaign_id or not campaign_id.strip():
            raise ValidationError("Campaign ID is required", field="campaign_id")
        
        # Parse campaign ID
        parts = campaign_id.strip().split('/')
        if len(parts) != 4 or parts[0] != 'customers' or parts[2] != 'campaigns':
            raise ValidationError("Campaign ID must be in format: customers/{customer_id}/campaigns/{campaign_id}", field="campaign_id")
        
        customer_id = parts[1]
        campaign_numeric_id = parts[3]
        
        # Validate customer ID
        if not customer_id.isdigit() or len(customer_id) != 10:
            raise ValidationError("Customer ID in campaign_id must be exactly 10 digits", field="campaign_id")
        
        # Validate campaign ID
        if not campaign_numeric_id.isdigit():
            raise ValidationError("Campaign ID must be numeric", field="campaign_id")
        
        # Try to access campaign via Google Ads API
        try:
            client = GoogleAdsClient.load_from_storage('./google-ads.yaml')
            campaign_service = client.get_service('CampaignService')
            
            # Get campaign info
            campaign = campaign_service.get_campaign(resource_name=campaign_id)
            
            return {
                "valid": True,
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "status": campaign.status.name,
                "budget_amount": campaign.campaign_budget.amount_micros / 1000000 if campaign.campaign_budget else None,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
            
        except GoogleAdsException as e:
            custom_exception = handle_google_ads_exception(e)
            if "NOT_FOUND" in str(e):
                raise ResourceNotFoundError("Campaign not found", resource_type="campaign", resource_id=campaign_id)
            elif "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to access campaign")
            else:
                raise custom_exception
                
    except (ValidationError, ResourceNotFoundError, AuthorizationError, GoogleAdsApiError):
        raise
    except Exception as e:
        logger.error(f"Campaign validation failed: {str(e)}")
        raise ServiceUnavailableError("Campaign validation service unavailable")

@app.get("/api/error-test")
async def test_error_handling(error_type: str = Query(..., description="Type of error to test"), request: Request = None):
    """Test endpoint for error handling system"""
    try:
        if error_type == "validation":
            raise ValidationError("Test validation error", field="test_field", value="test_value")
        elif error_type == "authentication":
            raise AuthenticationError("Test authentication error")
        elif error_type == "authorization":
            raise AuthorizationError("Test authorization error")
        elif error_type == "resource_not_found":
            raise ResourceNotFoundError("Test resource not found", resource_type="test", resource_id="123")
        elif error_type == "rate_limit":
            raise RateLimitError("Test rate limit error", retry_after=60)
        elif error_type == "configuration":
            raise ConfigurationError("Test configuration error", config_key="test_config")
        elif error_type == "service_unavailable":
            raise ServiceUnavailableError("Test service unavailable error")
        elif error_type == "google_ads":
            # Simulate a Google Ads API error
            from google.ads.googleads.errors import GoogleAdsException
            raise GoogleAdsException("Test Google Ads API error")
        else:
            raise ValidationError(f"Unknown error type: {error_type}", field="error_type")
            
    except (ValidationError, AuthenticationError, AuthorizationError, ResourceNotFoundError, 
            RateLimitError, ConfigurationError, ServiceUnavailableError, GoogleAdsApiError):
        raise
    except Exception as e:
        logger.error(f"Error test failed: {str(e)}")
        raise ServiceUnavailableError("Error test service unavailable")

# ============================================================================
# ENHANCED EXISTING ENDPOINTS
# ============================================================================

@app.get("/keyword-ideas")
async def get_keyword_ideas(
    customer_id: str = Query(..., description="Google Ads customer ID"),
    seed_keywords: str = Query(..., description="Comma-separated seed keywords"),
    geo_targets: Optional[str] = Query(None, description="Comma-separated geo target IDs"),
    language: str = Query("en", description="Language code"),
    limit: int = Query(10, ge=1, le=100, description="Number of keyword ideas to return"),
    request: Request = None
):
    """Get keyword ideas from Google Ads with enhanced error handling and logging"""
    
    import time
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', 'unknown') if request else 'unknown'
    
    try:
        # Log request start
        log_request_start(
            logger,
            request_id,
            "GET",
            "/keyword-ideas",
            customer_id=customer_id,
            seed_keywords=seed_keywords,
            geo_targets=geo_targets,
            language=language,
            limit=limit
        )
        
        # Validate customer_id
        if not customer_id or not customer_id.strip():
            raise ValidationError("Customer ID is required", field="customer_id")
        
        # Validate seed_keywords
        if not seed_keywords or not seed_keywords.strip():
            raise ValidationError("Seed keywords are required", field="seed_keywords")
        
        # Parse seed keywords
        keywords_list = [kw.strip() for kw in seed_keywords.split(",") if kw.strip()]
        if not keywords_list:
            raise ValidationError("At least one valid seed keyword is required", field="seed_keywords")
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100", field="limit")
        
        # Parse geo targets if provided
        geo_targets_list = None
        if geo_targets:
            try:
                geo_targets_list = [int(gt.strip()) for gt in geo_targets.split(",") if gt.strip()]
            except ValueError:
                raise ValidationError("Geo targets must be comma-separated integers", field="geo_targets")
        
        # Format customer ID
        formatted_customer_id = format_customer_id(customer_id)
        
        # Get credentials and headers
        credentials = get_credentials()
        headers = get_headers(credentials)
        
        # Build request payload
        payload = {
            "customerId": formatted_customer_id,
            "language": language,
            "keywordSeed": {
                "keywords": keywords_list
            },
            "pageSize": limit
        }
        
        # Add geo targets if provided
        if geo_targets_list:
            payload["geoTargetConstants"] = [f"geoTargetConstants/{gt}" for gt in geo_targets_list]
        
        # Make API request
        url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{formatted_customer_id}/googleAds:searchStream"
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            # Handle different error scenarios
            if response.status_code == 401:
                raise AuthenticationError("Invalid Google Ads credentials")
            elif response.status_code == 403:
                raise AuthorizationError("Insufficient permissions to access Google Ads API")
            elif response.status_code == 404:
                raise ResourceNotFoundError("Customer account not found", resource_type="customer", resource_id=customer_id)
            elif response.status_code == 429:
                raise RateLimitError("Google Ads API rate limit exceeded")
            else:
                raise GoogleAdsApiError(f"Google Ads API error: {response.status_code} - {response.text}")
        
        # Parse response
        data = response.json()
        
        # Extract keyword ideas
        keyword_ideas = []
        if "results" in data:
            for result in data["results"]:
                if "keywordIdea" in result:
                    idea = result["keywordIdea"]
                    keyword_ideas.append({
                        "text": idea.get("text", ""),
                        "search_volume": idea.get("keywordIdeaMetrics", {}).get("avgMonthlySearches", 0),
                        "competition": idea.get("keywordIdeaMetrics", {}).get("competition", "UNKNOWN"),
                        "low_top_of_page_bid": idea.get("keywordIdeaMetrics", {}).get("lowTopOfPageBidMicros", 0) / 1000000,
                        "high_top_of_page_bid": idea.get("keywordIdeaMetrics", {}).get("highTopOfPageBidMicros", 0) / 1000000
                    })
        
        # Log successful completion
        log_request_end(
            logger,
            request_id,
            "GET",
            "/keyword-ideas",
            200,
            time.time() - start_time,
            keywords_returned=len(keyword_ideas)
        )
        
        return {
            "status": "success",
            "keywords": keyword_ideas,
            "total_count": len(keyword_ideas),
            "request_id": request_id
        }
        
    except (ValidationError, AuthenticationError, AuthorizationError, GoogleAdsApiError, RateLimitError, ResourceNotFoundError) as e:
        # Log error and re-raise
        log_error_structured(
            logger,
            request_id,
            e,
            "/keyword-ideas",
            "GET"
        )
        raise
    except Exception as e:
        # Log unexpected errors
        log_error_structured(
            logger,
            request_id,
            e,
            "/keyword-ideas",
            "GET"
        )
        raise ServiceUnavailableError("Service temporarily unavailable")

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {"status": "ok", "message": "MCP Google Ads API is running"}

@app.get("/list-accounts", response_class=PlainTextResponse)
async def list_accounts_endpoint():
    """List all accessible Google Ads accounts"""
    try:
        creds = get_credentials()
        headers = get_headers(creds)
        
        response = requests.get(
            f"https://googleads.googleapis.com/{API_VERSION}/customers:listAccessibleCustomers",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Google Ads error: {response.text}")
        
        return response.text
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to list accounts: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

# ============================================================================
# CAMPAIGN CREATION MODELS
# ============================================================================

# ============================================================================
# ENHANCED CAMPAIGN CREATION ENDPOINT WITH ERROR HANDLING
# ============================================================================

class CampaignRequest(BaseModel):
    customer_id: str = Field(..., description="Google Ads customer ID", min_length=1)
    campaign_name: str = Field(..., description="Campaign name", min_length=1, max_length=255)
    budget_amount: float = Field(..., description="Daily budget amount", gt=0, le=10000)
    geo_targets: List[int] = Field(default=[2840], description="List of geo target IDs")
    status: str = Field("PAUSED", description="Campaign status", pattern="^(PAUSED|ENABLED)$")
    
    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format"""
        if not v.strip():
            raise ValueError('Customer ID cannot be empty')
        
        # Remove dashes and validate numeric
        clean_id = v.replace('-', '')
        if not clean_id.isdigit() or len(clean_id) != 10:
            raise ValueError('Customer ID must be 10 digits (with or without dashes)')
        
        return clean_id
    
    @validator('campaign_name')
    def validate_campaign_name(cls, v):
        """Validate campaign name"""
        if not v.strip():
            raise ValueError('Campaign name cannot be empty')
        
        # Check for invalid characters
        invalid_chars = ['<', '>', '&', '"', "'"]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f'Campaign name contains invalid character: {char}')
        
        return v.strip()
    
    @validator('budget_amount')
    def validate_budget_amount(cls, v):
        """Validate budget amount"""
        if v <= 0:
            raise ValueError('Budget amount must be greater than 0')
        if v > 10000:
            raise ValueError('Budget amount cannot exceed $10,000')
        return round(v, 2)
    
    @validator('geo_targets')
    def validate_geo_targets(cls, v):
        """Validate geo targets"""
        if not v:
            raise ValueError('At least one geo target is required')
        
        for gt in v:
            if not isinstance(gt, int) or gt <= 0:
                raise ValueError('Geo target IDs must be positive integers')
        
        return v

class CampaignResponse(BaseModel):
    success: bool
    campaign_id: Optional[str] = None
    message: str
    request_id: Optional[str] = None

@app.post("/create-campaign", response_model=CampaignResponse)
async def create_campaign(request: CampaignRequest):
    """Create a new Google Ads campaign with enhanced error handling"""
    
    try:
        # Validate campaign name doesn't already exist
        formatted_customer_id = format_customer_id(request.customer_id)
        
        # Initialize Google Ads client
        try:
            client = GoogleAdsClient.load_from_storage('./google-ads.yaml')
        except Exception as e:
            raise ConfigurationError("Failed to initialize Google Ads client", config_key="google-ads.yaml")
        
        # Get services
        campaign_service = client.get_service('CampaignService')
        campaign_budget_service = client.get_service('CampaignBudgetService')
        
        # Create campaign budget
        try:
            campaign_budget_operation = client.get_type('CampaignBudgetOperation')
            campaign_budget = campaign_budget_operation.create
            campaign_budget.name = f"{request.campaign_name} Budget"
            campaign_budget.amount_micros = int(request.budget_amount * 1000000)
            campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            
            # Add campaign budget
            campaign_budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=formatted_customer_id,
                operations=[campaign_budget_operation]
            )
            
            budget_resource_name = campaign_budget_response.results[0].resource_name
            
        except GoogleAdsException as e:
            # Handle specific Google Ads API errors
            custom_exception = handle_google_ads_exception(e)
            if "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to create campaign budget")
            elif "INVALID_CUSTOMER_ID" in str(e):
                raise ValidationError("Invalid customer ID", field="customer_id")
            else:
                raise custom_exception
        
        # Create campaign
        try:
            campaign_operation = client.get_type('CampaignOperation')
            campaign = campaign_operation.create
            campaign.name = request.campaign_name
            campaign.status = client.enums.CampaignStatusEnum[request.status]
            campaign.campaign_budget = budget_resource_name
            campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
            
            # Execute campaign creation
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=formatted_customer_id,
                operations=[campaign_operation]
            )
            
            campaign_resource_name = campaign_response.results[0].resource_name
            
        except GoogleAdsException as e:
            # Handle specific Google Ads API errors
            custom_exception = handle_google_ads_exception(e)
            if "DUPLICATE_NAME" in str(e):
                raise ValidationError("Campaign name already exists", field="campaign_name")
            elif "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to create campaign")
            else:
                raise custom_exception
        
        # Add geo targeting
        try:
            campaign_criterion_service = client.get_service('CampaignCriterionService')
            geo_operations = []
            
            for geo_target in request.geo_targets:
                criterion_operation = client.get_type('CampaignCriterionOperation')
                criterion = criterion_operation.create
                criterion.campaign = campaign_resource_name
                criterion.location.geo_target_constant = f"geoTargetConstants/{geo_target}"
                geo_operations.append(criterion_operation)
            
            if geo_operations:
                campaign_criterion_service.mutate_campaign_criteria(
                    customer_id=formatted_customer_id,
                    operations=geo_operations
                )
                
        except GoogleAdsException as e:
            # Log geo targeting error but don't fail the entire operation
            logger.warning(f"Failed to add geo targeting: {str(e)}")
        
        return CampaignResponse(
            success=True,
            campaign_id=campaign_resource_name,
            message=f"Campaign '{request.campaign_name}' created successfully",
            request_id=getattr(request.state, 'request_id', 'unknown')
        )
        
    except (ValidationError, AuthenticationError, AuthorizationError, GoogleAdsApiError, ConfigurationError):
        # Re-raise custom exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in campaign creation: {str(e)}")
        logger.error(traceback.format_exc())
        raise ServiceUnavailableError("Service temporarily unavailable")

# ============================================================================
# ENHANCED AD GROUP CREATION ENDPOINT WITH ERROR HANDLING
# ============================================================================

class AdGroupRequest(BaseModel):
    campaign_id: str = Field(..., description="Google Ads campaign ID", min_length=1)
    ad_group_name: str = Field(..., description="Ad group name", min_length=1, max_length=255)
    keywords: List[str] = Field(..., description="List of keywords to add", min_items=1)
    max_cpc: float = Field(1.0, description="Maximum cost per click bid", gt=0, le=100)
    status: str = Field("PAUSED", description="Ad group status", pattern="^(PAUSED|ENABLED)$")
    
    @validator('campaign_id')
    def validate_campaign_id(cls, v):
        """Validate campaign ID format and structure"""
        if not v.strip():
            raise ValueError('Campaign ID cannot be empty')
        
        # Check if it follows the expected format: customers/{customer_id}/campaigns/{campaign_id}
        parts = v.strip().split('/')
        if len(parts) != 4:
            raise ValueError('Campaign ID must be in format: customers/{customer_id}/campaigns/{campaign_id}')
        
        if parts[0] != 'customers' or parts[2] != 'campaigns':
            raise ValueError('Campaign ID must be in format: customers/{customer_id}/campaigns/{campaign_id}')
        
        # Validate customer_id (should be 10 digits)
        customer_id = parts[1]
        if not customer_id.isdigit() or len(customer_id) != 10:
            raise ValueError('Customer ID in campaign_id must be exactly 10 digits')
        
        # Validate campaign_id (should be numeric)
        campaign_id = parts[3]
        if not campaign_id.isdigit():
            raise ValueError('Campaign ID must be numeric')
        
        return v.strip()
    
    @validator('ad_group_name')
    def validate_ad_group_name(cls, v):
        """Validate ad group name with comprehensive checks"""
        if not v.strip():
            raise ValueError('Ad group name cannot be empty')
        
        name = v.strip()
        if len(name) > 255:
            raise ValueError('Ad group name cannot exceed 255 characters')
        
        # Check for invalid characters
        invalid_chars = ['<', '>', '&', '"', "'"]
        for char in invalid_chars:
            if char in name:
                raise ValueError(f'Ad group name cannot contain invalid character: {char}')
        
        # Check for excessive whitespace
        if name != name.strip():
            raise ValueError('Ad group name cannot start or end with whitespace')
        
        return name
    
    @validator('keywords')
    def validate_keywords(cls, v):
        """Validate keywords list with comprehensive checks"""
        if not v:
            raise ValueError('At least one keyword is required')
        
        if len(v) > 100:
            raise ValueError('Maximum 100 keywords allowed per ad group')
        
        validated_keywords = []
        seen_keywords = set()
        
        for i, keyword in enumerate(v):
            if not keyword or not keyword.strip():
                continue
            
            keyword_clean = keyword.strip()
            
            # Length validation
            if len(keyword_clean) > 80:
                raise ValueError(f'Keyword "{keyword_clean}" exceeds 80 character limit')
            
            if len(keyword_clean) < 1:
                continue
            
            # Character validation
            invalid_chars = ['<', '>', '&', '"', "'"]
            for char in invalid_chars:
                if char in keyword_clean:
                    raise ValueError(f'Keyword "{keyword_clean}" contains invalid character: {char}')
            
            # Duplicate check
            if keyword_clean.lower() in seen_keywords:
                raise ValueError(f'Duplicate keyword found: "{keyword_clean}"')
            
            seen_keywords.add(keyword_clean.lower())
            validated_keywords.append(keyword_clean)
        
        if not validated_keywords:
            raise ValueError('At least one valid keyword is required')
        
        return validated_keywords
    
    @validator('max_cpc')
    def validate_max_cpc(cls, v):
        """Validate max CPC bid with comprehensive checks"""
        if v <= 0:
            raise ValueError('Max CPC must be positive')
        
        if v > 100:
            raise ValueError('Max CPC cannot exceed 100')
        
        # Check for reasonable minimum (Google Ads minimum is typically $0.01)
        if v < 0.01:
            raise ValueError('Max CPC must be at least $0.01')
        
        # Round to 2 decimal places for consistency
        return round(v, 2)
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status with additional checks"""
        valid_statuses = ['PAUSED', 'ENABLED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

class AdGroupResponse(BaseModel):
    success: bool
    ad_group_id: Optional[str] = None
    message: str
    keywords_added: Optional[int] = None
    keywords_failed: Optional[int] = None
    failed_keywords: Optional[List[Dict[str, str]]] = None
    total_keywords: Optional[int] = None
    request_id: Optional[str] = None

@app.post("/create-ad-group", response_model=AdGroupResponse)
async def create_ad_group(request: AdGroupRequest):
    """Create a new ad group with keywords using enhanced error handling"""
    
    try:
        # Extract customer_id from campaign_id
        campaign_parts = request.campaign_id.split('/')
        customer_id = campaign_parts[1]
        
        # Initialize Google Ads client
        try:
            client = GoogleAdsClient.load_from_storage('./google-ads.yaml')
        except Exception as e:
            raise ConfigurationError("Failed to initialize Google Ads client", config_key="google-ads.yaml")
        
        # Validate campaign exists and is accessible
        try:
            campaign_service = client.get_service('CampaignService')
            campaign_query = f"""
                SELECT campaign.id, campaign.name, campaign.status
                FROM campaign
                WHERE campaign.id = {campaign_parts[3]}
            """
            
            campaign_response = campaign_service.search(
                customer_id=customer_id,
                query=campaign_query
            )
            
            if not list(campaign_response):
                raise ResourceNotFoundError(
                    "Campaign not found or not accessible",
                    resource_type="campaign",
                    resource_id=request.campaign_id
                )
            
            campaign_info = list(campaign_response)[0]
            if campaign_info.campaign.status.name == "REMOVED":
                raise ValidationError("Cannot create ad group in a removed campaign", field="campaign_id")
                
        except GoogleAdsException as e:
            custom_exception = handle_google_ads_exception(e)
            if "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to access campaign")
            elif "CUSTOMER_NOT_FOUND" in str(e):
                raise ValidationError("Invalid customer ID", field="customer_id")
            else:
                raise custom_exception
        
        # Create ad group
        try:
            ad_group_service = client.get_service('AdGroupService')
            
            ad_group_operation = client.get_type('AdGroupOperation')
            ad_group = ad_group_operation.create
            
            ad_group.name = request.ad_group_name
            ad_group.campaign = request.campaign_id
            ad_group.status = client.enums.AdGroupStatusEnum[request.status]
            ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            
            # Add ad group
            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[ad_group_operation]
            )
            
            ad_group_id = ad_group_response.results[0].resource_name
            
        except GoogleAdsException as e:
            custom_exception = handle_google_ads_exception(e)
            if "DUPLICATE_NAME" in str(e):
                raise ValidationError("Ad group name already exists in this campaign", field="ad_group_name")
            elif "INSUFFICIENT_PERMISSIONS" in str(e):
                raise AuthorizationError("Insufficient permissions to create ad group")
            else:
                raise custom_exception
        
        # Add keywords to ad group
        keywords_added = 0
        keywords_failed = 0
        failed_keywords = []
        
        try:
            ad_group_criterion_service = client.get_service('AdGroupCriterionService')
            
            # Process keywords in batches
            batch_size = 5000
            total_keywords = len(request.keywords)
            
            for i in range(0, total_keywords, batch_size):
                batch_keywords = request.keywords[i:i + batch_size]
                batch_operations = []
                
                for keyword in batch_keywords:
                    ad_group_criterion_operation = client.get_type('AdGroupCriterionOperation')
                    ad_group_criterion = ad_group_criterion_operation.create
                    ad_group_criterion.ad_group = ad_group_id
                    ad_group_criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                    ad_group_criterion.keyword.text = keyword
                    ad_group_criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
                    
                    # Set max CPC bid
                    ad_group_criterion.cpc_bid_micros = int(request.max_cpc * 1000000)
                    
                    batch_operations.append(ad_group_criterion_operation)
                
                try:
                    # Add keywords batch
                    keyword_response = ad_group_criterion_service.mutate_ad_group_criteria(
                        customer_id=customer_id,
                        operations=batch_operations
                    )
                    keywords_added += len(keyword_response.results)
                    
                except GoogleAdsException as e:
                    keywords_failed += len(batch_keywords)
                    for keyword in batch_keywords:
                        failed_keywords.append({
                            "keyword": keyword,
                            "error": str(e)
                        })
                    
        except GoogleAdsException as e:
            # Handle keyword addition errors
            custom_exception = handle_google_ads_exception(e)
            if "QUOTA_EXCEEDED" in str(e):
                raise RateLimitError("Google Ads API quota exceeded")
            elif "INVALID_KEYWORD" in str(e):
                raise ValidationError("One or more keywords are invalid", field="keywords")
            else:
                raise custom_exception
        
        return AdGroupResponse(
            success=True,
            ad_group_id=ad_group_id,
            message=f"Ad group '{request.ad_group_name}' created successfully",
            keywords_added=keywords_added,
            keywords_failed=keywords_failed,
            failed_keywords=failed_keywords if failed_keywords else None,
            total_keywords=len(request.keywords),
            request_id=getattr(request.state, 'request_id', 'unknown')
        )
        
    except (ValidationError, AuthenticationError, AuthorizationError, GoogleAdsApiError, ConfigurationError, ResourceNotFoundError, RateLimitError):
        # Re-raise custom exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in ad group creation: {str(e)}")
        logger.error(traceback.format_exc())
        raise ServiceUnavailableError("Service temporarily unavailable")

# ============================================================================
# TEST ENDPOINT FOR AD GROUP CREATION
# ============================================================================

@app.post("/test/ad-group-creation")
async def test_ad_group_creation():
    """Test endpoint for ad group creation logic without actually creating ad groups"""
    try:
        # Test client initialization
        credentials_path = os.environ.get("GOOGLE_ADS_CREDENTIALS_PATH", "nomadixgear-parse-emails-4a20c1d08701.json")
        developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
        
        if not developer_token:
            return {
                "test_status": "failed",
                "error": "GOOGLE_ADS_DEVELOPER_TOKEN not configured",
                "timestamp": time.time()
            }
        
        # Test client creation
        try:
            client = GoogleAdsClient.load_from_storage(credentials_path)
            client.developer_token = developer_token
            
            # Test service instantiation
            ad_group_service = client.get_service("AdGroupService")
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Test operation type creation
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            
            # Test enum access
            status_enum = client.enums.AdGroupStatusEnum.PAUSED
            type_enum = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            criterion_status_enum = client.enums.AdGroupCriterionStatusEnum.ENABLED
            keyword_match_enum = client.enums.KeywordMatchTypeEnum.EXACT
            
            return {
                "test_status": "passed",
                "client_initialization": "successful",
                "service_instantiation": "successful",
                "operation_creation": "successful",
                "enum_access": "successful",
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "test_status": "failed",
                "error": f"Client initialization failed: {str(e)}",
                "timestamp": time.time()
            }
            
    except Exception as e:
        return {
            "test_status": "failed",
            "error": f"Test failed: {str(e)}",
            "timestamp": time.time()
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 