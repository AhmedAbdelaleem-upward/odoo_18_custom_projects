"""
Standardized response helpers for Simple API.
Ensures consistent response format across all endpoints.
"""

from typing import Any, Dict, List, Optional
from ..core.constants import (
    RESPONSE_KEY_SUCCESS,
    RESPONSE_KEY_DATA,
    RESPONSE_KEY_COUNT,
)


def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data (dict, list, or single item)
        message: Optional success message

    Returns:
        {"success": True, "data": data}
    """
    response = {
        RESPONSE_KEY_SUCCESS: True,
        RESPONSE_KEY_DATA: data,
    }
    if message:
        response["message"] = message
    return response


def success_list_response(data: List[Any], count: int, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized success response for lists with count.

    Args:
        data: List of items
        count: Total count
        message: Optional success message

    Returns:
        {"success": True, "data": data, "count": count}
    """
    response = {
        RESPONSE_KEY_SUCCESS: True,
        RESPONSE_KEY_DATA: data,
        RESPONSE_KEY_COUNT: count,
    }
    if message:
        response["message"] = message
    return response
