# -*- coding: utf-8 -*-

import functools
import logging
from typing import Callable

from fastapi import HTTPException, status
from odoo.exceptions import AccessError, UserError, ValidationError as OdooValidationError

from ..core.exceptions import BaseAPIException

_logger = logging.getLogger(__name__)


def handle_router_errors(func: Callable) -> Callable:
    """
    Decorator to handle common errors in router functions.
    Converts Odoo exceptions to appropriate HTTP responses.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseAPIException:
            # Re-raise our custom exceptions as-is
            raise
        except AccessError as e:
            _logger.warning(f"Access denied: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except (UserError, OdooValidationError) as e:
            _logger.warning(f"Validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            _logger.exception(f"Unexpected error in {func.__name__}: {type(e).__name__}: {e}")
            # In debug mode, show actual error; in production, hide it
            detail = f"{type(e).__name__}: {str(e)}"  # TODO: make configurable
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail,
            )

    return wrapper
