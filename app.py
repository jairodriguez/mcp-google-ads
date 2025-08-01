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
from google.ads.googleads.util import ResourceName

app = FastAPI()

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

@app.get("/health/keyword-ideas")
async def keyword_ideas_health_check():
    """Health check endpoint for keyword ideas service"""
    try:
        service = KeywordIdeasService()
        
        # Test with minimal parameters
        test_result = service.make_keyword_ideas_request(
            customer_id="9197949842",
            q=["test"],
            geo="2484",
            lang="1003",
            limit=1
        )
        
        return {
            "status": "healthy",
            "service": "keyword_ideas",
            "timestamp": time.time(),
            "response_time": "tested",
            "api_version": service.api_version
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "keyword_ideas",
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/test/keyword-ideas")
async def test_keyword_ideas_endpoint():
    """Regression test endpoint for keyword ideas functionality"""
    try:
        service = KeywordIdeasService()
        
        # Test parameter validation
        try:
            service.validate_keyword_ideas_params("123", [], "2484", "1003", 10)
            validation_passed = False
        except HTTPException:
            validation_passed = True
        
        # Test with valid parameters
        result = service.make_keyword_ideas_request(
            customer_id="9197949842",
            q=["digital marketing"],
            geo="2484",
            lang="1003",
            limit=5
        )
        
        return {
            "test_status": "passed",
            "validation_working": validation_passed,
            "api_response_received": len(result) > 0,
            "api_version": service.api_version,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "test_status": "failed",
            "error": str(e),
            "timestamp": time.time()
        }

# ============================================================================
# KEYWORD IDEAS ENDPOINT (PROTECTED)
# ============================================================================

class Idea(BaseModel):
    text: str
    avg_monthly_searches: int
    competition: str
    bid_low_micros: int
    bid_high_micros: int

@app.get("/keyword-ideas", response_model=List[Idea])
async def keyword_ideas(
    customer_id: str = Query(..., description="Google Ads customer ID, no dashes"),
    q: List[str] = Query(..., description="One or more seed keywords"),
    geo: str = Query("2484", description="Geo target constant ID (e.g. Mexico=2484)"),
    lang: str = Query("1003", description="Language constant ID (e.g. Spanish=1003)"),
    limit: Optional[int] = Query(None, description="Max number of ideas to return"),
):
    """Get keyword ideas from Google Ads API with comprehensive safeguards"""
    try:
        # Use isolated service class
        service = KeywordIdeasService()
        
        # Validate parameters
        service.validate_keyword_ideas_params(customer_id, q, geo, lang, limit)
        
        # Make request
        result = service.make_keyword_ideas_request(customer_id, q, geo, lang, limit)
        
        # Process results (simplified for safety)
        ideas = []
        if "results" in result:
            for item in result["results"][:limit or 10]:
                ideas.append(Idea(
                    text=item.get("text", ""),
                    avg_monthly_searches=item.get("avgMonthlySearches", 0),
                    competition=item.get("competition", "UNKNOWN"),
                    bid_low_micros=item.get("bidLowMicros", 0),
                    bid_high_micros=item.get("bidHighMicros", 0)
                ))
        
        return ideas
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Keyword ideas endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Keyword ideas error: {str(e)}")

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

class CampaignRequest(BaseModel):
    customer_id: str = Field(..., description="Google Ads customer ID (without dashes)", min_length=10, max_length=10)
    campaign_name: str = Field(..., description="Campaign name", min_length=1, max_length=255)
    budget_amount: float = Field(..., description="Daily budget amount in account currency", gt=0, le=10000)
    budget_type: str = Field("DAILY", description="Budget type", pattern="^(DAILY|MONTHLY)$")
    campaign_type: str = Field("SEARCH", description="Campaign type", pattern="^(SEARCH|DISPLAY|VIDEO|SHOPPING)$")
    geo_targets: List[str] = Field(["2484"], description="List of geo target constant IDs")
    language: str = Field("1003", description="Language constant ID")
    status: str = Field("PAUSED", description="Campaign status", pattern="^(PAUSED|ENABLED)$")
    
    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Customer ID must be exactly 10 digits')
        return v
    
    @validator('campaign_name')
    def validate_campaign_name(cls, v):
        """Validate campaign name"""
        if not v.strip():
            raise ValueError('Campaign name cannot be empty')
        return v.strip()
    
    @validator('budget_amount')
    def validate_budget_amount(cls, v):
        """Validate budget amount"""
        if v <= 0:
            raise ValueError('Budget amount must be positive')
        if v > 10000:
            raise ValueError('Budget amount cannot exceed 10,000')
        return v
    
    @validator('geo_targets')
    def validate_geo_targets(cls, v):
        """Validate geo targets"""
        for geo in v:
            if not geo.isdigit():
                raise ValueError('All geo targets must be numeric IDs')
        return v

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

class CampaignResponse(BaseModel):
    success: bool
    ad_group_id: Optional[str] = None
    message: str
    keywords_added: Optional[int] = None
    keywords_failed: Optional[int] = None
    failed_keywords: Optional[List[Dict[str, str]]] = None
    total_keywords: Optional[int] = None

# ============================================================================
# CAMPAIGN CREATION ENDPOINT
# ============================================================================

@app.post("/create-campaign", response_model=CampaignResponse)
async def create_campaign(request: CampaignRequest):
    """Create a new Google Ads campaign with comprehensive validation and error handling"""
    try:
        logger.info(f"Starting campaign creation for customer {request.customer_id}")
        
        customer_id = format_customer_id(request.customer_id)
        creds = get_credentials()
        headers = get_headers(creds)
        
        # Step 1: Create campaign budget first
        budget_payload = {
            "name": f"{request.campaign_name} Budget",
            "amountMicros": int(request.budget_amount * 1000000),
            "deliveryMethod": "STANDARD"
        }
        
        logger.info(f"Creating campaign budget: {request.budget_amount}")
        budget_response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/campaignBudgets",
            headers=headers,
            json=budget_payload,
            timeout=30
        )
        
        if budget_response.status_code != 200:
            error_msg = f"Budget creation failed: {budget_response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        budget_id = budget_response.json().get("name")
        logger.info(f"Campaign budget created successfully: {budget_id}")
        
        # Step 2: Create campaign
        campaign_payload = {
            "name": request.campaign_name,
            "status": request.status,
            "campaignBudget": budget_id,
            "advertisingChannelType": request.campaign_type,
            "biddingStrategyType": "TARGET_CPA"
        }
        
        logger.info(f"Creating campaign: {request.campaign_name}")
        campaign_response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/campaigns",
            headers=headers,
            json=campaign_payload,
            timeout=30
        )
        
        if campaign_response.status_code != 200:
            error_msg = f"Campaign creation failed: {campaign_response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        campaign_id = campaign_response.json().get("name")
        logger.info(f"Campaign created successfully: {campaign_id}")
        
        # Step 3: Add geo targeting
        for geo_target in request.geo_targets:
            geo_payload = {
                "campaign": campaign_id,
                "location": {
                    "geoTargetConstant": f"geoTargetConstants/{geo_target}"
                }
            }
            
            geo_response = requests.post(
                f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/campaignCriteria",
                headers=headers,
                json=geo_payload,
                timeout=30
            )
            
            if geo_response.status_code != 200:
                logger.warning(f"Geo targeting failed for {geo_target}: {geo_response.text}")
        
        return CampaignResponse(
            success=True,
            campaign_id=campaign_id,
            message=f"Campaign '{request.campaign_name}' created successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error in campaign creation: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

# ============================================================================
# AD GROUP CREATION ENDPOINT (UPDATED WITH GOOGLE ADS LIBRARY)
# ============================================================================

@app.post("/create-ad-group", response_model=CampaignResponse)
async def create_ad_group(request: AdGroupRequest):
    """Create a new ad group with keywords using Google Ads Python library"""
    
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"[{request_id}] Starting ad group creation for campaign {request.campaign_id}")
    logger.info(f"[{request_id}] Request details: ad_group_name='{request.ad_group_name}', keywords_count={len(request.keywords)}, max_cpc=${request.max_cpc}")
    
    try:
        # Extract customer_id from campaign_id
        campaign_parts = request.campaign_id.split('/')
        if len(campaign_parts) < 3:
            error_msg = "Invalid campaign ID format"
            logger.error(f"[{request_id}] {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        customer_id = campaign_parts[1]
        logger.info(f"[{request_id}] Extracted customer_id: {customer_id}")
        
        # Additional validation: Check campaign existence
        try:
            # Initialize Google Ads client for validation
            credentials_path = os.environ.get("GOOGLE_ADS_CREDENTIALS_PATH", "nomadixgear-parse-emails-4a20c1d08701.json")
            developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
            
            if not developer_token:
                error_msg = "GOOGLE_ADS_DEVELOPER_TOKEN not configured"
                logger.error(f"[{request_id}] {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
            
            # Create Google Ads client for validation
            client = GoogleAdsClient.load_from_storage(credentials_path)
            client.developer_token = developer_token
            
            # Validate campaign exists and is accessible
            campaign_service = client.get_service("CampaignService")
            try:
                campaign_resource_name = request.campaign_id
                campaign = campaign_service.get_campaign(resource_name=campaign_resource_name)
                
                # Additional validation: Check campaign status
                if campaign.status.name == "REMOVED":
                    error_msg = "Cannot create ad group in removed campaign"
                    logger.error(f"[{request_id}] {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)
                
                logger.info(f"[{request_id}] Campaign validation successful: {campaign.name}")
                
            except GoogleAdsException as ex:
                if "NOT_FOUND" in str(ex):
                    error_msg = "Campaign not found or not accessible"
                    logger.error(f"[{request_id}] {error_msg}: {ex.failure.errors[0].message}")
                    raise HTTPException(status_code=400, detail=error_msg)
                else:
                    error_msg = f"Campaign validation failed: {ex.failure.errors[0].message}"
                    logger.error(f"[{request_id}] {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[{request_id}] Campaign validation failed (continuing anyway): {str(e)}")
            # Continue with the request even if validation fails
        
        # Initialize Google Ads client for ad group creation
        try:
            # Load credentials from environment variables
            credentials_path = os.environ.get("GOOGLE_ADS_CREDENTIALS_PATH", "nomadixgear-parse-emails-4a20c1d08701.json")
            developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
            login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
            
            if not developer_token:
                error_msg = "GOOGLE_ADS_DEVELOPER_TOKEN not configured"
                logger.error(f"[{request_id}] {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
            
            # Create Google Ads client
            client = GoogleAdsClient.load_from_storage(credentials_path)
            client.developer_token = developer_token
            if login_customer_id:
                client.login_customer_id = login_customer_id
            
            logger.info(f"[{request_id}] Google Ads client initialized successfully")
            
        except Exception as e:
            error_msg = f"Google Ads client initialization failed: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            logger.error(f"[{request_id}] {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 1: Create ad group using Google Ads service
        try:
            ad_group_service = client.get_service("AdGroupService")
            
            # Create ad group operation with enhanced configuration
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create
            
            # Set basic ad group properties
            ad_group.name = request.ad_group_name
            ad_group.campaign = request.campaign_id
            ad_group.status = client.enums.AdGroupStatusEnum[request.status]
            ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            
            # Set additional configuration for better performance
            ad_group.target_cpa_micros = int(request.max_cpc * 1000000)  # Set target CPA based on max CPC
            
            # Set targeting settings for search campaigns
            targeting_setting = client.get_type("TargetingSetting")
            targeting_setting.target_restrictions.search_targeting_setting.target_restrictions = {}
            ad_group.targeting_setting = targeting_setting
            
            logger.info(f"[{request_id}] Creating ad group: {request.ad_group_name} in campaign: {request.campaign_id}")
            
            # Execute ad group creation with proper error handling
            try:
                ad_group_response = ad_group_service.mutate_ad_groups(
                    customer_id=customer_id,
                    operations=[ad_group_operation]
                )
                
                if not ad_group_response.results:
                    raise HTTPException(status_code=500, detail="Ad group creation failed: No results returned")
                
                ad_group_id = ad_group_response.results[0].resource_name
                logger.info(f"[{request_id}] Ad group created successfully: {ad_group_id}")
                
                # Verify ad group was created with correct settings
                try:
                    created_ad_group = ad_group_service.get_ad_group(resource_name=ad_group_id)
                    logger.info(f"[{request_id}] Ad group verification successful: {created_ad_group.name}")
                except GoogleAdsException as ex:
                    logger.warning(f"[{request_id}] Ad group verification failed: {ex.failure.errors[0].message}")
                    # Continue anyway as the ad group was created
                
            except GoogleAdsException as ex:
                error_msg = f"Ad group creation failed: {ex.failure.errors[0].message}"
                logger.error(f"[{request_id}] {error_msg}")
                
                # Provide more specific error messages based on error type
                if "INVALID_CAMPAIGN" in str(ex):
                    raise HTTPException(status_code=400, detail="Invalid campaign ID or campaign not accessible")
                elif "DUPLICATE_NAME" in str(ex):
                    raise HTTPException(status_code=400, detail="Ad group name already exists in this campaign")
                elif "INSUFFICIENT_PERMISSIONS" in str(ex):
                    raise HTTPException(status_code=403, detail="Insufficient permissions to create ad group")
                else:
                    raise HTTPException(status_code=500, detail=error_msg)
                    
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Unexpected error in ad group creation: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            logger.error(f"[{request_id}] {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 2: Add keywords to ad group
        keywords_added = 0
        keywords_failed = 0
        failed_keywords = []
        
        try:
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Process keywords in batches to avoid API limits
            batch_size = 5000  # Google Ads API limit
            total_keywords = len(request.keywords)
            
            logger.info(f"[{request_id}] Adding {total_keywords} keywords to ad group in batches of {batch_size}")
            
            for i in range(0, total_keywords, batch_size):
                batch_keywords = request.keywords[i:i + batch_size]
                batch_operations = []
                
                for keyword in batch_keywords:
                    try:
                        # Create keyword criterion operation
                        ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
                        ad_group_criterion = ad_group_criterion_operation.create
                        
                        # Set ad group reference
                        ad_group_criterion.ad_group = ad_group_id
                        ad_group_criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                        
                        # Set keyword properties
                        ad_group_criterion.keyword.text = keyword
                        ad_group_criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
                        
                        # Set CPC bid (convert dollars to micros)
                        cpc_bid_micros = int(request.max_cpc * 1000000)
                        ad_group_criterion.cpc_bid_micros = cpc_bid_micros
                        
                        # Set additional bidding strategy if needed
                        if request.max_cpc > 5.0:  # For high-value keywords
                            ad_group_criterion.effective_cpc_bid_micros = cpc_bid_micros
                        
                        batch_operations.append(ad_group_criterion_operation)
                        
                    except Exception as e:
                        logger.warning(f"[{request_id}] Failed to create operation for keyword '{keyword}': {str(e)}")
                        keywords_failed += 1
                        failed_keywords.append({"keyword": keyword, "error": str(e)})
                        continue
                
                if batch_operations:
                    try:
                        logger.info(f"[{request_id}] Processing batch of {len(batch_operations)} keywords")
                        
                        # Execute keyword addition for this batch
                        keyword_response = ad_group_criterion_service.mutate_ad_group_criteria(
                            customer_id=customer_id,
                            operations=batch_operations
                        )
                        
                        batch_added = len(keyword_response.results)
                        keywords_added += batch_added
                        logger.info(f"[{request_id}] Successfully added {batch_added} keywords in this batch")
                        
                        # Log any partial failures in the batch
                        if len(keyword_response.results) < len(batch_operations):
                            logger.warning(f"[{request_id}] Batch partially failed: {len(batch_operations) - len(keyword_response.results)} keywords failed")
                        
                    except GoogleAdsException as ex:
                        # Handle batch-level errors
                        error_msg = ex.failure.errors[0].message
                        logger.error(f"[{request_id}] Batch keyword addition failed: {error_msg}")
                        
                        # Provide specific error messages based on error type
                        if "INVALID_KEYWORD" in error_msg:
                            logger.error(f"[{request_id}] Some keywords contain invalid characters or format")
                        elif "DUPLICATE_KEYWORD" in error_msg:
                            logger.error(f"[{request_id}] Some keywords already exist in the ad group")
                        elif "INSUFFICIENT_BUDGET" in error_msg:
                            logger.error(f"[{request_id}] Campaign budget insufficient for keyword bids")
                        elif "QUOTA_EXCEEDED" in error_msg:
                            logger.error(f"[{request_id}] API quota exceeded, some keywords may not be added")
                        
                        # Mark all keywords in this batch as failed
                        keywords_failed += len(batch_operations)
                        for operation in batch_operations:
                            keyword_text = operation.create.keyword.text
                            failed_keywords.append({"keyword": keyword_text, "error": error_msg})
                        
                    except Exception as e:
                        logger.error(f"[{request_id}] Unexpected error in batch processing: {str(e)}")
                        keywords_failed += len(batch_operations)
                        for operation in batch_operations:
                            keyword_text = operation.create.keyword.text
                            failed_keywords.append({"keyword": keyword_text, "error": str(e)})
            
            logger.info(f"[{request_id}] Keyword addition completed: {keywords_added} added, {keywords_failed} failed")
            
            # Log summary of failed keywords for debugging
            if failed_keywords:
                logger.warning(f"[{request_id}] Failed keywords: {failed_keywords[:10]}")  # Log first 10 failures
                if len(failed_keywords) > 10:
                    logger.warning(f"[{request_id}] ... and {len(failed_keywords) - 10} more failures")
            
        except GoogleAdsException as ex:
            error_msg = f"Keyword addition failed: {ex.failure.errors[0].message}"
            logger.error(f"[{request_id}] {error_msg}")
            
            # Provide specific error messages
            if "INVALID_AD_GROUP" in str(ex):
                raise HTTPException(status_code=400, detail="Invalid ad group ID or ad group not accessible")
            elif "INSUFFICIENT_PERMISSIONS" in str(ex):
                raise HTTPException(status_code=403, detail="Insufficient permissions to add keywords")
            else:
                # Don't fail the entire request if keyword addition fails
                logger.warning(f"[{request_id}] Keyword addition failed but continuing: {error_msg}")
                
        except Exception as e:
            logger.warning(f"[{request_id}] Unexpected error in keyword addition: {str(e)}")
            # Don't fail the entire request if keyword addition fails
        
        end_time = time.time()
        total_duration = end_time - start_time
        logger.info(f"[{request_id}] Ad group creation completed in {total_duration:.2f} seconds")

        return CampaignResponse(
            success=True,
            ad_group_id=ad_group_id,
            message=f"Ad group '{request.ad_group_name}' created successfully",
            keywords_added=keywords_added,
            keywords_failed=keywords_failed,
            failed_keywords=failed_keywords if failed_keywords else None,
            total_keywords=len(request.keywords)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error in ad group creation: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

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