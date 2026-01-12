"""
Decorator utilities for Simple API.

Provides error handling decorators for routers.
"""

import logging
import inspect
from functools import wraps
from typing import Callable
from fastapi import HTTPException, status
from odoo.exceptions import UserError, AccessError, ValidationError as OdooValidationError

from ..core.exceptions import BaseAPIException, ValidationError

_logger = logging.getLogger(__name__)


def handle_router_errors(func: Callable) -> Callable:
    """
    Decorator for FastAPI router endpoints to standardize error handling.
    Supports both synchronous and asynchronous functions.

    Catches:
    - BaseAPIException: Re-raises as-is (already HTTPException)
    - UserError/AccessError: Converts to appropriate HTTP exceptions
    - Generic exceptions: Converts to 500 Internal Server Error

    Usage:
        @router.get("/")
        @handle_router_errors
        def get_items(auth: dict = Depends(jwt_auth)):
            # Your code here
    """
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Let FastAPI HTTPException pass through
                raise
            except BaseAPIException:
                raise
            except AccessError as e:
                _logger.warning("Access denied: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e)
                )
            except (UserError, OdooValidationError) as e:
                _logger.warning("Validation error: %s", str(e))
                raise ValidationError(detail=str(e))
            except Exception as e:
                _logger.exception("Unexpected error in router: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )
        return wrapper
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Let FastAPI HTTPException pass through
                raise
            except BaseAPIException:
                raise
            except AccessError as e:
                _logger.warning("Access denied: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(e)
                )
            except (UserError, OdooValidationError) as e:
                _logger.warning("Validation error: %s", str(e))
                raise ValidationError(detail=str(e))
            except Exception as e:
                _logger.exception("Unexpected error in router: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )
        return wrapper
