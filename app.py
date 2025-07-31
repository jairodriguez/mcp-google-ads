from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from pydantic import BaseModel
import uvicorn
import os

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

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "MCP Google Ads API is running"}

@app.get("/list-accounts", response_class=PlainTextResponse)
async def list_accounts_endpoint():
    """List all accessible Google Ads accounts"""
    try:
        creds = get_credentials()
        headers = get_headers(creds)
        
        url = f"https://googleads.googleapis.com/{API_VERSION}/customers:listAccessibleCustomers"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return f"Error accessing accounts: {response.text}"
        
        customers = response.json()
        if not customers.get('resourceNames'):
            return "No accessible accounts found."
        
        # Format the results
        result_lines = ["Accessible Google Ads Accounts:"]
        result_lines.append("-" * 50)
        
        for resource_name in customers['resourceNames']:
            customer_id = resource_name.split('/')[-1]
            formatted_id = format_customer_id(customer_id)
            result_lines.append(f"Account ID: {formatted_id}")
        
        return "\n".join(result_lines)
    
    except Exception as e:
        return f"Error listing accounts: {str(e)}"

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
    """Get keyword ideas from Google Ads API"""
    try:
        # Format customer ID
        customer_id = format_customer_id(customer_id)
        
        # Get credentials
        creds = get_credentials()
        headers = get_headers(creds)
        
        # Prepare the request payload for the correct endpoint
        payload = {
            "customerId": customer_id,
            "keywordSeed": {"keywords": q},
            "language": f"languageConstants/{lang}",
            "geoTargetConstants": [f"geoTargetConstants/{geo}"]
        }
        
        if limit:
            payload["pageSize"] = limit
        
        # Make the API call to the correct endpoint
        response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}:generateKeywordIdeas",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Google Ads error: {response.text}")
        
        data = response.json()
        ideas = []
        
        # Parse the response
        for result in data.get("results", []):
            if "keywordIdeaMetrics" in result:
                metrics = result["keywordIdeaMetrics"]
                ideas.append(Idea(
                    text=result.get("text", ""),
                    avg_monthly_searches=metrics.get("avgMonthlySearches", 0),
                    competition=metrics.get("competition", "UNSPECIFIED"),
                    bid_low_micros=metrics.get("lowTopOfPageBidMicros", 0),
                    bid_high_micros=metrics.get("highTopOfPageBidMicros", 0)
                ))
        
        return ideas
        
    except Exception as e:
        logger.error(f"Error in keyword_ideas: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Google Ads error: {str(e)}")

# Campaign Creation Models
class CampaignRequest(BaseModel):
    customer_id: str
    campaign_name: str
    budget_amount: float
    budget_type: str = "DAILY"  # DAILY or MONTHLY
    campaign_type: str = "SEARCH"  # SEARCH, DISPLAY, VIDEO, etc.
    geo_targets: List[str] = ["2484"]  # Mexico by default
    language: str = "1003"  # Spanish by default
    status: str = "PAUSED"  # PAUSED or ENABLED

class AdGroupRequest(BaseModel):
    campaign_id: str
    ad_group_name: str
    keywords: List[str]
    max_cpc: float = 1.0
    status: str = "PAUSED"

class CampaignResponse(BaseModel):
    success: bool
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    message: str

@app.post("/create-campaign", response_model=CampaignResponse)
async def create_campaign(request: CampaignRequest):
    """Create a new Google Ads campaign"""
    try:
        customer_id = format_customer_id(request.customer_id)
        creds = get_credentials()
        headers = get_headers(creds)
        
        # Step 1: Create campaign budget first
        budget_payload = {
            "name": f"{request.campaign_name} Budget",
            "amountMicros": int(request.budget_amount * 1000000),
            "deliveryMethod": "STANDARD"
        }
        
        budget_response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/campaignBudgets",
            headers=headers,
            json=budget_payload,
            timeout=30
        )
        
        if budget_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Budget creation failed: {budget_response.text}")
        
        budget_data = budget_response.json()
        budget_resource_name = budget_data.get("resourceName")
        
        # Step 2: Create campaign with proper v19 structure
        campaign_payload = {
            "name": request.campaign_name,
            "status": request.status.upper(),
            "campaignBudget": budget_resource_name,
            "advertisingChannelType": "SEARCH",
            "biddingStrategyType": "MAXIMIZE_CONVERSIONS",
            "targetingSetting": {
                "targetRestrictions": {
                    "geoTargetType": {
                        "positiveGeoTargetType": "PRESENCE_OR_INTEREST",
                        "negativeGeoTargetType": "PRESENCE"
                    }
                }
            }
        }
        
        # Create campaign using the correct v19 endpoint
        response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/campaigns",
            headers=headers,
            json=campaign_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Campaign creation failed: {response.text}")
        
        campaign_data = response.json()
        campaign_resource_name = campaign_data.get("resourceName")
        campaign_id = campaign_resource_name.split("/")[-1] if campaign_resource_name else None
        
        # Step 3: Add geo targeting if specified
        if request.geo_targets and campaign_resource_name:
            for geo_target in request.geo_targets:
                geo_payload = {
                    "campaign": campaign_resource_name,
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
                    logger.warning(f"Failed to add geo target {geo_target}: {geo_response.text}")
        
        return CampaignResponse(
            success=True,
            campaign_id=campaign_id,
            message=f"Campaign '{request.campaign_name}' created successfully with ID: {campaign_id}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Campaign creation error: {str(e)}")

@app.post("/create-ad-group", response_model=CampaignResponse)
async def create_ad_group(request: AdGroupRequest):
    """Create a new ad group within a campaign"""
    try:
        # Extract customer_id from campaign_id if not provided
        campaign_parts = request.campaign_id.split("/")
        if len(campaign_parts) >= 2:
            customer_id = format_customer_id(campaign_parts[1])
        else:
            customer_id = format_customer_id(request.campaign_id)
        
        creds = get_credentials()
        headers = get_headers(creds)
        
        # Create ad group with proper v19 structure
        ad_group_payload = {
            "name": request.ad_group_name,
            "status": request.status.upper(),
            "campaign": f"customers/{customer_id}/campaigns/{request.campaign_id}",
            "type": "SEARCH_STANDARD",
            "cpcBidMicros": int(request.max_cpc * 1000000)
        }
        
        response = requests.post(
            f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/adGroups",
            headers=headers,
            json=ad_group_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ad group creation failed: {response.text}")
        
        ad_group_data = response.json()
        ad_group_resource_name = ad_group_data.get("resourceName")
        ad_group_id = ad_group_resource_name.split("/")[-1] if ad_group_resource_name else None
        
        # Add keywords to the ad group
        keywords_added = 0
        for keyword in request.keywords:
            keyword_payload = {
                "adGroup": ad_group_resource_name,
                "keyword": {
                    "text": keyword,
                    "matchType": "PHRASE"
                }
            }
            
            keyword_response = requests.post(
                f"https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/adGroupCriteria",
                headers=headers,
                json=keyword_payload,
                timeout=30
            )
            
            if keyword_response.status_code == 200:
                keywords_added += 1
            else:
                logger.warning(f"Failed to add keyword '{keyword}': {keyword_response.text}")
        
        return CampaignResponse(
            success=True,
            ad_group_id=ad_group_id,
            message=f"Ad group '{request.ad_group_name}' created successfully with ID: {ad_group_id}. Keywords added: {keywords_added}/{len(request.keywords)}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error creating ad group: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ad group creation error: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 