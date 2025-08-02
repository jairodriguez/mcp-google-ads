"""
Comprehensive Logging Configuration for Google Ads MCP API

This module provides structured logging configuration with:
- Different log levels for different error types
- Request ID correlation
- Stack trace inclusion
- Sensitive information filtering
- Log rotation and storage
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json
import traceback
from pathlib import Path

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add error details for exceptions
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add performance metrics if available
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        
        # Add Google Ads specific information
        if hasattr(record, 'google_ads_error_code'):
            log_entry['google_ads_error_code'] = record.google_ads_error_code
        
        if hasattr(record, 'google_ads_request_id'):
            log_entry['google_ads_request_id'] = record.google_ads_request_id
        
        return json.dumps(log_entry, ensure_ascii=False)

class SensitiveFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    def __init__(self):
        super().__init__()
        self.sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'token[=:]\s*\S+',
            r'key[=:]\s*\S+',
            r'secret[=:]\s*\S+',
            r'credential[=:]\s*\S+',
            r'authorization[=:]\s*\S+',
            r'api_key[=:]\s*\S+',
            r'developer_token[=:]\s*\S+'
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive information from log messages"""
        if hasattr(record, 'msg'):
            import re
            message = str(record.msg)
            for pattern in self.sensitive_patterns:
                message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
            record.msg = message
        
        return True

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """Setup comprehensive logging configuration"""
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = StructuredFormatter()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveFilter())
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file and log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveFilter())
        root_logger.addHandler(file_handler)
    
    # Create application logger
    app_logger = logging.getLogger('google_ads_mcp')
    app_logger.setLevel(getattr(logging, log_level.upper()))
    
    return app_logger

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_request_start(logger: logging.Logger, request_id: str, method: str, path: str, **kwargs):
    """Log the start of a request"""
    logger.info(
        "Request started",
        extra={
            'request_id': request_id,
            'method': method,
            'endpoint': path,
            'extra_fields': kwargs
        }
    )

def log_request_end(logger: logging.Logger, request_id: str, method: str, path: str, 
                   status_code: int, duration: float, **kwargs):
    """Log the end of a request"""
    logger.info(
        "Request completed",
        extra={
            'request_id': request_id,
            'method': method,
            'endpoint': path,
            'status_code': status_code,
            'duration': duration,
            'extra_fields': kwargs
        }
    )

def log_error(logger: logging.Logger, request_id: str, error: Exception, 
              endpoint: str = None, method: str = None, **kwargs):
    """Log an error with context"""
    extra_fields = {
        'request_id': request_id,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'extra_fields': kwargs
    }
    
    if endpoint:
        extra_fields['endpoint'] = endpoint
    
    if method:
        extra_fields['method'] = method
    
    # Add Google Ads specific information if available
    if hasattr(error, 'google_ads_error_code'):
        extra_fields['google_ads_error_code'] = error.google_ads_error_code
    
    if hasattr(error, 'google_ads_request_id'):
        extra_fields['google_ads_request_id'] = error.google_ads_request_id
    
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra=extra_fields
    )

def log_validation_error(logger: logging.Logger, request_id: str, field: str, 
                        value: Any, message: str, **kwargs):
    """Log a validation error"""
    logger.warning(
        f"Validation error: {message}",
        extra={
            'request_id': request_id,
            'validation_field': field,
            'validation_value': str(value),
            'validation_message': message,
            'extra_fields': kwargs
        }
    )

def log_google_ads_error(logger: logging.Logger, request_id: str, error: Exception, 
                        operation: str = None, **kwargs):
    """Log a Google Ads API error"""
    extra_fields = {
        'request_id': request_id,
        'google_ads_error_type': type(error).__name__,
        'google_ads_error_message': str(error),
        'extra_fields': kwargs
    }
    
    if operation:
        extra_fields['google_ads_operation'] = operation
    
    # Extract Google Ads specific error information
    if hasattr(error, 'failure') and error.failure:
        if hasattr(error.failure, 'errors') and error.failure.errors:
            first_error = error.failure.errors[0]
            extra_fields['google_ads_error_code'] = first_error.error_code.request_error.name if first_error.error_code else None
            extra_fields['google_ads_error_message'] = first_error.message
    
    logger.error(
        f"Google Ads API error: {str(error)}",
        exc_info=True,
        extra=extra_fields
    )

def log_performance(logger: logging.Logger, request_id: str, operation: str, 
                   duration: float, success: bool, **kwargs):
    """Log performance metrics"""
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        f"Performance: {operation}",
        extra={
            'request_id': request_id,
            'operation': operation,
            'duration': duration,
            'success': success,
            'extra_fields': kwargs
        }
    )

def log_security_event(logger: logging.Logger, request_id: str, event_type: str, 
                      details: Dict[str, Any], **kwargs):
    """Log security-related events"""
    logger.warning(
        f"Security event: {event_type}",
        extra={
            'request_id': request_id,
            'security_event_type': event_type,
            'security_details': details,
            'extra_fields': kwargs
        }
    )

# ============================================================================
# LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware:
    """Middleware for comprehensive request logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    async def __call__(self, request, call_next):
        import time
        
        # Generate request ID if not present
        request_id = getattr(request.state, 'request_id', None)
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request start
        log_request_start(
            self.logger,
            request_id,
            request.method,
            request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent', 'Unknown')
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request end
            log_request_end(
                self.logger,
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(duration)
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            log_error(
                self.logger,
                request_id,
                e,
                request.url.path,
                request.method,
                duration=duration
            )
            
            # Re-raise the exception
            raise

# ============================================================================
# LOGGING CONFIGURATION HELPERS
# ============================================================================

def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration from environment variables"""
    return {
        'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
        'log_file': os.environ.get('LOG_FILE', 'logs/app.log'),
        'max_bytes': int(os.environ.get('LOG_MAX_BYTES', 10 * 1024 * 1024)),  # 10MB
        'backup_count': int(os.environ.get('LOG_BACKUP_COUNT', 5)),
        'enable_console': os.environ.get('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
        'enable_file': os.environ.get('LOG_ENABLE_FILE', 'true').lower() == 'true'
    }

def initialize_logging() -> logging.Logger:
    """Initialize logging with default configuration"""
    config = get_logging_config()
    return setup_logging(**config)

# ============================================================================
# LOGGING DECORATORS
# ============================================================================

def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with timing"""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Function {func.__name__} completed successfully",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'success': True
                    }
                )
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'success': False,
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Function {func.__name__} completed successfully",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'success': True
                    }
                )
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'success': False,
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator 