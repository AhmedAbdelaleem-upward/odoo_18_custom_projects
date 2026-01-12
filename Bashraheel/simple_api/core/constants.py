# Service Names
SERVICE_AUTH = 'simple.auth.service'
SERVICE_JWT = 'simple.jwt.service'
SERVICE_PRODUCT = 'simple.product.service'

# Token Types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# JWT Configuration
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
DEFAULT_JWT_SECRET = "simple-api-secret-key-change-in-production"

# System Parameters
PARAM_KEY_JWT_SECRET = "simple_api.jwt_secret_key"
PARAM_KEY_ACCESS_EXPIRE_MIN = "simple_api.access_token_expire_minutes"
PARAM_KEY_REFRESH_EXPIRE_DAYS = "simple_api.refresh_token_expire_days"

# Response Keys
RESPONSE_KEY_SUCCESS = "success"
RESPONSE_KEY_DATA = "data"
RESPONSE_KEY_COUNT = "count"

# Error Messages
ERROR_MSG_INVALID_CREDENTIALS = "Invalid email or password"
ERROR_MSG_USER_INACTIVE = "User account is inactive"
ERROR_MSG_INVALID_OR_EXPIRED_TOKEN = "Invalid or expired token"
ERROR_MSG_INVALID_TOKEN_PAYLOAD = "Invalid token payload"
ERROR_MSG_NOT_FOUND = "Resource not found"
