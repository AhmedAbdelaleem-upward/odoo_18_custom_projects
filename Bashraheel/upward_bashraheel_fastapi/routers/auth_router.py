# -*- coding: utf-8 -*-

from fastapi import APIRouter
from odoo import api

import logging

from ..schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenData,
    RefreshTokenData,
    UserSchema,
)
from ..core.constants import SERVICE_AUTH, SERVICE_JWT, TOKEN_TYPE_REFRESH
from ..utils.decorators import handle_router_errors

_logger = logging.getLogger(__name__)


def create_auth_router(registry, uid, context):
    """
    Factory function to create the auth router with Odoo context.

    Args:
        registry: Odoo registry
        uid: User ID
        context: Odoo context

    Returns:
        APIRouter: FastAPI router with auth endpoints
    """
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post(
        "/login",
        response_model=LoginResponse,
        summary="User login",
        description="Authenticate user and return JWT tokens",
    )
    @handle_router_errors
    def login(request: LoginRequest) -> LoginResponse:
        """
        Authenticate user with email and password.

        Returns JWT access and refresh tokens on success.
        """
        _logger.info(f"Login attempt for: {request.login}")

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)
            auth_service = env[SERVICE_AUTH]
            jwt_service = env[SERVICE_JWT]

            # Authenticate user
            user_data = auth_service.authenticate_user(request.login, request.password)

            # Generate tokens
            access_token = jwt_service.generate_access_token(user_data)
            refresh_token = jwt_service.generate_refresh_token(user_data)
            expires_in = jwt_service.get_token_expiry_seconds()

            return LoginResponse(
                success=True,
                data=TokenData(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    token_type="Bearer",
                    user=UserSchema(
                        id=user_data["user_id"],
                        email=user_data["email"],
                        name=user_data["name"],
                        phone=user_data.get("phone"),
                    ),
                ),
            )

    @router.post(
        "/refresh",
        response_model=RefreshTokenResponse,
        summary="Refresh access token",
        description="Get new access token using refresh token",
    )
    @handle_router_errors
    def refresh_token(request: RefreshTokenRequest) -> RefreshTokenResponse:
        """
        Refresh the access token using a valid refresh token.

        Returns new access and refresh tokens.
        """
        _logger.info("Token refresh requested")

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)
            auth_service = env[SERVICE_AUTH]
            jwt_service = env[SERVICE_JWT]

            # Validate refresh token
            payload = jwt_service.validate_token(request.refresh_token, TOKEN_TYPE_REFRESH)

            user_id = payload.get("user_id")

            # Verify user is still active
            auth_service.validate_user_active(user_id)

            # Get fresh user data
            user_data = auth_service.get_user_by_id(user_id)

            # Generate new tokens
            new_access_token = jwt_service.generate_access_token(user_data)
            new_refresh_token = jwt_service.generate_refresh_token(user_data)
            expires_in = jwt_service.get_token_expiry_seconds()

            return RefreshTokenResponse(
                success=True,
                data=RefreshTokenData(
                    access_token=new_access_token,
                    refresh_token=new_refresh_token,
                    expires_in=expires_in,
                    token_type="Bearer",
                ),
            )

    return router
