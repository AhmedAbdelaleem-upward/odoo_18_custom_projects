# -*- coding: utf-8 -*-

"""
JWT Authentication dependencies for FastAPI endpoints.
"""

import logging
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from odoo import api

from ..core.constants import SERVICE_JWT, TOKEN_TYPE_ACCESS
from ..core.exceptions import (
    InvalidOrExpiredTokenError,
    JWTUnauthorizedError,
    UserInactive,
)

_logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for Swagger UI
# Note: auto_error=False allows custom error handling in verify_jwt_token
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="JWT access token. Get it from POST /auth/login, then enter: Bearer YOUR_TOKEN"
)


def create_jwt_auth_dependency(registry, uid, context):
    """
    Factory function to create a JWT authentication dependency.

    Args:
        registry: Odoo registry
        uid: User ID
        context: Odoo context

    Returns:
        Callable: FastAPI dependency function that validates JWT and returns auth context
    """

    def verify_jwt_token(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> dict:
        """
        Verify JWT token and return authentication context.

        Args:
            credentials: HTTP Authorization credentials (Bearer token)

        Returns:
            dict: Authentication context with user_id, partner_id, email

        Raises:
            JWTUnauthorizedError: If no token provided
            InvalidOrExpiredTokenError: If token is invalid or expired
            UserInactive: If user is inactive
        """
        if not credentials:
            raise JWTUnauthorizedError("Authorization header missing")

        token = credentials.credentials

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)
            jwt_service = env[SERVICE_JWT]

            # Validate the token
            payload = jwt_service.validate_token(token, TOKEN_TYPE_ACCESS)

            user_id = payload.get("user_id")
            partner_id = payload.get("partner_id")
            email = payload.get("email")

            if not user_id:
                raise InvalidOrExpiredTokenError("Invalid token payload")

            # Verify user is still active
            user = env["res.users"].sudo().browse(user_id)
            if not user.exists() or not user.active:
                raise UserInactive("User account is inactive")

            return {
                "user_id": user_id,
                "partner_id": partner_id,
                "email": email,
            }

    return verify_jwt_token
