import logging
from typing import Dict, Any, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from odoo import api

from ..core.exceptions import InvalidOrExpiredTokenError, InvalidTokenPayloadError
from ..core.constants import TOKEN_TYPE_ACCESS, SERVICE_JWT

_logger = logging.getLogger(__name__)

# FastAPI security scheme for Bearer token
security = HTTPBearer()


def create_jwt_auth_dependency(registry, uid, context) -> Callable:
    """
    Factory function to create a JWT authentication dependency with Odoo context.

    Args:
        registry: Odoo registry
        uid: User ID
        context: Odoo context dict

    Returns:
        Function that can be used as FastAPI dependency
    """

    def jwt_auth(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        FastAPI dependency to authenticate requests using JWT tokens.
        Validates the JWT token and returns payload and user context.

        Args:
            credentials: Authorization header credentials

        Returns:
            Dict with user_id, partner_id, email, token_payload

        Raises:
            InvalidOrExpiredTokenError: If token is invalid or expired
            InvalidTokenPayloadError: If token payload is missing required fields
            HTTPException: For other authentication errors
        """
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                # Validate JWT token
                jwt_service = env[SERVICE_JWT]
                payload = jwt_service.validate_token(
                    credentials.credentials,
                    TOKEN_TYPE_ACCESS
                )

                if not payload:
                    raise InvalidOrExpiredTokenError()

                # Extract user ID from token
                user_id = payload.get("user_id")
                if not user_id:
                    raise InvalidTokenPayloadError()

                _logger.debug("Auth successful for user %d", user_id)

                # Return authentication context
                return {
                    "user_id": int(user_id),
                    "partner_id": payload.get("partner_id"),
                    "email": payload.get("email"),
                    "token_payload": payload
                }

        except (InvalidOrExpiredTokenError, InvalidTokenPayloadError):
            # Re-raise JWT exceptions (they inherit from HTTPException)
            raise
        except Exception as e:
            _logger.error("Authentication error: %s", str(e))
            # For non-JWT errors, raise generic unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return jwt_auth
