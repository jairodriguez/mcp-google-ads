"""
Centralized Error Handling Module for Google Ads MCP API

This module provides comprehensive error handling functionality including:
- Custom exception classes for different error types
- Structured error responses with request IDs
- Detailed logging for debugging
- Google Ads API specific error handling
"""

import logging
import uuid
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from google.ads.googleads.errors import GoogleAdsException
from pydantic import ValidationError as PydanticValidationError
import re

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# CUSTOM EXCEPTION CLASSES
# ============================================================================

class BaseAPIException(Exception):
    """Base exception class for all API errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

class ValidationError(BaseAPIException):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details or {"field": field, "value": value},
            status_code=status.HTTP_400_BAD_REQUEST
        )

class AuthenticationError(BaseAPIException):
    """Exception raised for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed", 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationError(BaseAPIException):
    """Exception raised for authorization errors"""
    
    def __init__(self, message: str = "Insufficient permissions", 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )

class GoogleAdsApiError(BaseAPIException):
    """Exception raised for Google Ads API errors"""
    
    def __init__(self, message: str, google_ads_error_code: Optional[str] = None,
                 google_ads_request_id: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="GOOGLE_ADS_API_ERROR",
            details=details or {
                "google_ads_error_code": google_ads_error_code,
                "google_ads_request_id": google_ads_request_id
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

class RateLimitError(BaseAPIException):
    """Exception raised for rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details or {"retry_after": retry_after},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class ResourceNotFoundError(BaseAPIException):
    """Exception raised for resource not found errors"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=details or {"resource_type": resource_type, "resource_id": resource_id},
            status_code=status.HTTP_404_NOT_FOUND
        )

class ConfigurationError(BaseAPIException):
    """Exception raised for configuration errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details or {"config_key": config_key},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ServiceUnavailableError(BaseAPIException):
    """Exception raised for service unavailability"""
    
    def __init__(self, message: str = "Service temporarily unavailable", 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

# ============================================================================
# ERROR RESPONSE UTILITIES
# ============================================================================

def create_error_response(
    request: Request,
    exception: BaseAPIException,
    include_stack_trace: bool = False
) -> JSONResponse:
    """Create a standardized error response"""
    
    # Get request ID from request state
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Build error response
    error_response = {
        "status": "error",
        "message": exception.message,
        "error_code": exception.error_code,
        "request_id": request_id,
        "timestamp": exception.timestamp.isoformat(),
        "details": exception.details
    }
    
    # Include stack trace in development mode
    if include_stack_trace:
        error_response["stack_trace"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=exception.status_code,
        content=error_response
    )

def sanitize_error_message(message: str, include_details: bool = False) -> str:
    """Sanitize error messages for production"""
    if not include_details:
        # Remove sensitive information from error messages
        sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'token[=:]\s*\S+',
            r'key[=:]\s*\S+',
            r'secret[=:]\s*\S+',
            r'credential[=:]\s*\S+'
        ]
        
        for pattern in sensitive_patterns:
            message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
    
    return message

# ============================================================================
# GOOGLE ADS API ERROR HANDLING
# ============================================================================

def handle_google_ads_exception(google_ads_exception: GoogleAdsException) -> GoogleAdsApiError:
    """Convert Google Ads API exception to our custom exception"""
    
    # Extract error information from Google Ads exception
    if google_ads_exception.failure and google_ads_exception.failure.errors:
        error = google_ads_exception.failure.errors[0]
        error_message = error.message
        error_code = error.error_code.request_error.name if error.error_code else None
        request_id = google_ads_exception.request_id if hasattr(google_ads_exception, 'request_id') else None
    else:
        error_message = str(google_ads_exception)
        error_code = None
        request_id = None
    
    # Map Google Ads error codes to user-friendly messages
    user_friendly_messages = {
        "INVALID_CUSTOMER_ID": "Invalid customer ID provided",
        "CUSTOMER_NOT_FOUND": "Customer account not found",
        "INSUFFICIENT_PERMISSIONS": "Insufficient permissions to access this resource",
        "QUOTA_EXCEEDED": "API quota exceeded. Please try again later",
        "RATE_EXCEEDED": "Request rate exceeded. Please slow down your requests",
        "INTERNAL_ERROR": "Google Ads API internal error. Please try again",
        "DEADLINE_EXCEEDED": "Request timed out. Please try again",
        "UNAUTHENTICATED": "Authentication failed. Please check your credentials",
        "PERMISSION_DENIED": "Permission denied. Please check your access rights",
        "NOT_FOUND": "Resource not found",
        "ALREADY_EXISTS": "Resource already exists",
        "FAILED_PRECONDITION": "Operation failed due to invalid state",
        "ABORTED": "Operation was aborted",
        "OUT_OF_RANGE": "Value is out of valid range",
        "UNIMPLEMENTED": "Operation not implemented",
        "UNAVAILABLE": "Service is currently unavailable",
        "DATA_LOSS": "Data loss occurred",
        "UNKNOWN": "Unknown error occurred"
    }
    
    # Use user-friendly message if available
    if error_code and error_code in user_friendly_messages:
        error_message = user_friendly_messages[error_code]
    
    return GoogleAdsApiError(
        message=error_message,
        google_ads_error_code=error_code,
        google_ads_request_id=request_id,
        details={
            "original_message": str(google_ads_exception),
            "error_code": error_code,
            "request_id": request_id
        }
    )

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_error(
    request: Request,
    exception: Exception,
    level: str = "error",
    include_stack_trace: bool = True
) -> None:
    """Log error with contextual information"""
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Build log context
    log_context = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "error_type": type(exception).__name__,
        "error_message": str(exception)
    }
    
    # Add additional context for custom exceptions
    if isinstance(exception, BaseAPIException):
        log_context.update({
            "error_code": exception.error_code,
            "status_code": exception.status_code,
            "details": exception.details
        })
    
    # Add stack trace if requested
    if include_stack_trace:
        log_context["stack_trace"] = traceback.format_exc()
    
    # Log with appropriate level
    if level == "error":
        logger.error("API Error", extra=log_context)
    elif level == "warning":
        logger.warning("API Warning", extra=log_context)
    elif level == "info":
        logger.info("API Info", extra=log_context)
    else:
        logger.debug("API Debug", extra=log_context)

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that required fields are present"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )

def validate_field_type(value: Any, field_name: str, expected_type: type) -> None:
    """Validate field type"""
    if not isinstance(value, expected_type):
        raise ValidationError(
            message=f"Field '{field_name}' must be of type {expected_type.__name__}",
            field=field_name,
            value=value
        )

def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: Optional[int] = None) -> None:
    """Validate string length"""
    if not isinstance(value, str):
        raise ValidationError(
            message=f"Field '{field_name}' must be a string",
            field=field_name,
            value=value
        )
    
    if len(value) < min_length:
        raise ValidationError(
            message=f"Field '{field_name}' must be at least {min_length} characters long",
            field=field_name,
            value=value
        )
    
    if max_length and len(value) > max_length:
        raise ValidationError(
            message=f"Field '{field_name}' must be no more than {max_length} characters long",
            field=field_name,
            value=value
        )

# ============================================================================
# REQUEST ID MIDDLEWARE
# ============================================================================

async def add_request_id_middleware(request: Request, call_next):
    """Middleware to add request ID to all requests"""
    
    # Generate request ID if not present
    if not hasattr(request.state, 'request_id'):
        request.state.request_id = str(uuid.uuid4())
    
    # Process request
    response = await call_next(request)
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request.state.request_id
    
    return response

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors"""
    log_error(request, exc, level="warning", include_stack_trace=False)
    return create_error_response(request, exc)

async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Handle authentication errors"""
    log_error(request, exc, level="warning", include_stack_trace=False)
    return create_error_response(request, exc)

async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Handle authorization errors"""
    log_error(request, exc, level="warning", include_stack_trace=False)
    return create_error_response(request, exc)

async def google_ads_exception_handler(request: Request, exc: GoogleAdsException) -> JSONResponse:
    """Handle Google Ads API errors"""
    # Convert to our custom exception
    custom_exception = handle_google_ads_exception(exc)
    log_error(request, custom_exception, level="error", include_stack_trace=True)
    return create_error_response(request, custom_exception)

async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    # Convert Pydantic validation error to our custom exception
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    custom_exception = ValidationError(
        message="Validation failed",
        details={"validation_errors": error_details}
    )
    
    log_error(request, custom_exception, level="warning", include_stack_trace=False)
    return create_error_response(request, custom_exception)

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""
    # Create a generic exception for unexpected errors
    generic_exception = BaseAPIException(
        message="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    log_error(request, exc, level="error", include_stack_trace=True)
    return create_error_response(request, generic_exception) 