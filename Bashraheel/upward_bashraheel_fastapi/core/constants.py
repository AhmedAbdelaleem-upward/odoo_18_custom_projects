# -*- coding: utf-8 -*-

# Service names
SERVICE_INVOICE = "bashraheel.invoice.service"
SERVICE_JWT = "bashraheel.jwt.service"
SERVICE_AUTH = "bashraheel.auth.service"

# JWT Configuration
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
DEFAULT_JWT_SECRET = "bashraheel-fastapi-secret-key-change-in-production"

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# System parameter keys for JWT config
PARAM_KEY_JWT_SECRET = "upward_bashraheel_fastapi.jwt_secret_key"
PARAM_KEY_ACCESS_EXPIRE_MIN = "upward_bashraheel_fastapi.access_token_expire_minutes"
PARAM_KEY_REFRESH_EXPIRE_DAYS = "upward_bashraheel_fastapi.refresh_token_expire_days"

# Response keys
KEY_SUCCESS = "success"
KEY_DATA = "data"
KEY_COUNT = "count"
KEY_MESSAGE = "message"
KEY_STATUS = "status"

# Status values
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"

# Error messages
ERROR_INVALID_REQUEST = "Invalid request data"
ERROR_INVOICE_NOT_FOUND = "Invoice not found"
ERROR_STORE_NOT_FOUND = "Store not found"
ERROR_MISSING_STORE_ID = "Store ID is required"
ERROR_MISSING_DATE = "Date is required"
ERROR_MISSING_INVOICE_LIST = "Invoice list is required"
ERROR_EMPTY_INVOICE_LIST = "Invoice list cannot be empty"
ERROR_INTERNAL_SERVER = "Internal server error"
