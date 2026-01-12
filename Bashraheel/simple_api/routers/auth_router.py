import logging
from fastapi import APIRouter, status
from odoo import api

from ..schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from ..core.constants import TOKEN_TYPE_REFRESH, SERVICE_AUTH, SERVICE_JWT
from ..core.exceptions import AuthenticationFailed, UserInactive
from ..utils.responses import success_response
from ..utils.decorators import handle_router_errors

_logger = logging.getLogger(__name__)


def create_auth_router(registry, uid, context):
    """Create and return the authentication API router"""
    router = APIRouter(
        prefix="/auth",
        tags=["Authentication"],
    )

    @router.post(
        "/login",
        response_model=LoginResponse,
        status_code=status.HTTP_200_OK,
        summary="User Login",
        description="Authenticate user with email and password",
    )
    @handle_router_errors
    def login(request: LoginRequest):
        """
        Authenticate user and return JWT tokens.

        Args:
            request: Login credentials (email, password)

        Returns:
            LoginResponse with access token, refresh token, and user data
        """
        with registry.cursor() as cr:
            env = api.Environment(cr, uid, context)

            auth_service = env[SERVICE_AUTH]
            user_data = auth_service.authenticate_user(
                request.email,
                request.password
            )

            jwt_service = env[SERVICE_JWT]
            access_token = jwt_service.generate_access_token(user_data)
            refresh_token = jwt_service.generate_refresh_token(user_data)
            expires_in = jwt_service.get_token_expiry_seconds()

            cr.commit()

            response_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "user": user_data,
            }

            return success_response(response_data)

    @router.post(
        "/refresh",
        response_model=RefreshTokenResponse,
        status_code=status.HTTP_200_OK,
        summary="Refresh Access Token",
        description="Get new access token using refresh token",
    )
    @handle_router_errors
    def refresh(request: RefreshTokenRequest):
        """
        Refresh JWT tokens.

        Args:
            request: Refresh token request

        Returns:
            RefreshTokenResponse with new access and refresh tokens
        """
        with registry.cursor() as cr:
            env = api.Environment(cr, uid, context)

            jwt_service = env[SERVICE_JWT]
            payload = jwt_service.validate_token(
                request.refresh_token,
                token_type=TOKEN_TYPE_REFRESH
            )

            if not payload:
                raise AuthenticationFailed(
                    detail="Invalid or expired refresh token"
                )

            partner_id = payload.get("partner_id")
            if not partner_id:
                raise AuthenticationFailed(detail="Invalid token payload")

            auth_service = env[SERVICE_AUTH]
            if not auth_service.validate_user_active(partner_id):
                raise UserInactive()

            user_data = auth_service.get_user_by_id(partner_id)

            access_token = jwt_service.generate_access_token(user_data)
            new_refresh_token = jwt_service.generate_refresh_token(user_data)
            expires_in = jwt_service.get_token_expiry_seconds()

            cr.commit()

            response_data = {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "expires_in": expires_in,
            }

            return success_response(response_data)

    return router
