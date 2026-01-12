from fastapi import status, HTTPException
from typing import Optional
from .constants import (
    ERROR_MSG_INVALID_CREDENTIALS,
    ERROR_MSG_USER_INACTIVE,
    ERROR_MSG_INVALID_OR_EXPIRED_TOKEN,
    ERROR_MSG_INVALID_TOKEN_PAYLOAD,
    ERROR_MSG_NOT_FOUND,
)


# Base Exception
class BaseAPIException(HTTPException):
    """Root exception for all Simple API exceptions"""
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = "API error"
    ):
        super().__init__(status_code=status_code, detail=detail)


# Authentication Exceptions (401)
class JWTUnauthorizedError(BaseAPIException):
    """Generic JWT authentication exception"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            detail=detail or "Authentication required",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidOrExpiredTokenError(JWTUnauthorizedError):
    """Invalid or expired token"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__(detail=detail or ERROR_MSG_INVALID_OR_EXPIRED_TOKEN)


class InvalidTokenPayloadError(JWTUnauthorizedError):
    """Invalid token payload"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__(detail=detail or ERROR_MSG_INVALID_TOKEN_PAYLOAD)


class AuthenticationFailed(JWTUnauthorizedError):
    """Authentication failed - invalid credentials"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__(detail=detail or ERROR_MSG_INVALID_CREDENTIALS)


class UserInactive(JWTUnauthorizedError):
    """User inactive exception"""
    def __init__(self, detail: Optional[str] = None):
        super().__init__(detail=detail or ERROR_MSG_USER_INACTIVE)


# Resource Not Found (404)
class ResourceNotFoundError(BaseAPIException):
    """Generic resource not found"""
    def __init__(
        self,
        detail: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None
    ):
        if resource_type and resource_id:
            detail = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail or ERROR_MSG_NOT_FOUND
        )


# Validation Exceptions (400)
class ValidationError(BaseAPIException):
    """Generic validation error"""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
