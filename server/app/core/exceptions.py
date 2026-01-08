"""
Custom Exceptions

Application-specific exceptions with HTTP status codes.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception (404)."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message=message, status_code=404, details=details)


class BadRequestException(AppException):
    """Bad request exception (400)."""
    
    def __init__(self, message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class UnauthorizedException(AppException):
    """Unauthorized exception (401)."""
    
    def __init__(self, message: str = "Unauthorized", details: Optional[Any] = None):
        super().__init__(message=message, status_code=401, details=details)


class ForbiddenException(AppException):
    """Forbidden exception (403)."""
    
    def __init__(self, message: str = "Forbidden", details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, details=details)


class ConflictException(AppException):
    """Conflict exception (409)."""
    
    def __init__(self, message: str = "Conflict", details: Optional[Any] = None):
        super().__init__(message=message, status_code=409, details=details)


class ValidationException(AppException):
    """Validation exception (422)."""
    
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None):
        super().__init__(message=message, status_code=422, details=details)


class InternalServerException(AppException):
    """Internal server error exception (500)."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


class ServiceUnavailableException(AppException):
    """Service unavailable exception (503)."""
    
    def __init__(self, message: str = "Service unavailable", details: Optional[Any] = None):
        super().__init__(message=message, status_code=503, details=details)
