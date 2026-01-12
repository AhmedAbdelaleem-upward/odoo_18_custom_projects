# -*- coding: utf-8 -*-

from typing import Any, List, Optional

from ..core.constants import (
    KEY_SUCCESS,
    KEY_DATA,
    KEY_COUNT,
    KEY_MESSAGE,
    KEY_STATUS,
    STATUS_SUCCESS,
    STATUS_ERROR,
)


def success_response(data: Any, message: Optional[str] = None) -> dict:
    """Create a standard success response"""
    response = {KEY_STATUS: STATUS_SUCCESS, KEY_DATA: data}
    if message:
        response[KEY_MESSAGE] = message
    return response


def success_list_response(
    data: List[Any], count: Optional[int] = None, message: Optional[str] = None
) -> dict:
    """Create a standard success response for list data"""
    response = {
        KEY_STATUS: STATUS_SUCCESS,
        KEY_DATA: data,
        KEY_COUNT: count if count is not None else len(data),
    }
    if message:
        response[KEY_MESSAGE] = message
    return response


def error_response(message: str, data: Any = None) -> dict:
    """Create a standard error response"""
    response = {KEY_STATUS: STATUS_ERROR, KEY_MESSAGE: message}
    if data is not None:
        response[KEY_DATA] = data
    return response
