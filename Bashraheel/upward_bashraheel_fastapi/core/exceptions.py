# -*- coding: utf-8 -*-

from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for all API errors"""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = "An error occurred",
    ):
        super().__init__(status_code=status_code, detail=detail)


class ValidationError(BaseAPIException):
    """Raised when request validation fails"""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ResourceNotFoundError(BaseAPIException):
    """Raised when a requested resource is not found"""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InvoiceCreationError(BaseAPIException):
    """Raised when invoice creation fails"""

    def __init__(self, detail: str = "Failed to create invoice"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class StoreNotFoundError(BaseAPIException):
    """Raised when store/journal is not found"""

    def __init__(self, detail: str = "Store not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InternalServerError(BaseAPIException):
    """Raised for internal server errors"""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


# Authentication Exceptions
class JWTUnauthorizedError(BaseAPIException):
    """Base class for JWT authentication errors"""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidOrExpiredTokenError(JWTUnauthorizedError):
    """Raised when token is invalid or expired"""

    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(detail=detail)


class InvalidTokenPayloadError(JWTUnauthorizedError):
    """Raised when token payload is invalid"""

    def __init__(self, detail: str = "Invalid token payload"):
        super().__init__(detail=detail)


class AuthenticationFailed(JWTUnauthorizedError):
    """Raised when authentication fails"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail=detail)


class UserInactive(JWTUnauthorizedError):
    """Raised when user is inactive"""

    def __init__(self, detail: str = "User is inactive"):
        super().__init__(detail=detail)
