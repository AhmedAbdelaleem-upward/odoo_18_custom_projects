# -*- coding: utf-8 -*-

import jwt
from datetime import datetime, timedelta
from odoo import models, api
import logging

from ..core.constants import (
    SERVICE_JWT,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
    DEFAULT_JWT_SECRET,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    PARAM_KEY_JWT_SECRET,
    PARAM_KEY_ACCESS_EXPIRE_MIN,
    PARAM_KEY_REFRESH_EXPIRE_DAYS,
)
from ..core.exceptions import InvalidOrExpiredTokenError, InvalidTokenPayloadError

_logger = logging.getLogger(__name__)


class JWTService(models.AbstractModel):
    """Service for JWT token generation and validation"""

    _name = SERVICE_JWT
    _description = "Bashraheel JWT Service"

    def _get_jwt_secret(self) -> str:
        """Get JWT secret from system parameters or use default"""
        param = self.env["ir.config_parameter"].sudo()
        return param.get_param(PARAM_KEY_JWT_SECRET, DEFAULT_JWT_SECRET)

    def _get_access_token_expire_minutes(self) -> int:
        """Get access token expiry in minutes from system parameters"""
        param = self.env["ir.config_parameter"].sudo()
        value = param.get_param(
            PARAM_KEY_ACCESS_EXPIRE_MIN, str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        try:
            return int(value)
        except (ValueError, TypeError):
            return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

    def _get_refresh_token_expire_days(self) -> int:
        """Get refresh token expiry in days from system parameters"""
        param = self.env["ir.config_parameter"].sudo()
        value = param.get_param(
            PARAM_KEY_REFRESH_EXPIRE_DAYS, str(DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
        )
        try:
            return int(value)
        except (ValueError, TypeError):
            return DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

    def generate_access_token(self, user_data: dict) -> str:
        """
        Generate an access token for the user.

        Args:
            user_data: Dictionary containing user_id, partner_id, email

        Returns:
            str: JWT access token
        """
        expire_minutes = self._get_access_token_expire_minutes()
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)

        payload = {
            "user_id": user_data.get("user_id"),
            "partner_id": user_data.get("partner_id"),
            "email": user_data.get("email"),
            "type": TOKEN_TYPE_ACCESS,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self._get_jwt_secret(), algorithm=DEFAULT_JWT_ALGORITHM)

    def generate_refresh_token(self, user_data: dict) -> str:
        """
        Generate a refresh token for the user.

        Args:
            user_data: Dictionary containing user_id, partner_id, email

        Returns:
            str: JWT refresh token
        """
        expire_days = self._get_refresh_token_expire_days()
        expire = datetime.utcnow() + timedelta(days=expire_days)

        payload = {
            "user_id": user_data.get("user_id"),
            "partner_id": user_data.get("partner_id"),
            "email": user_data.get("email"),
            "type": TOKEN_TYPE_REFRESH,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self._get_jwt_secret(), algorithm=DEFAULT_JWT_ALGORITHM)

    def validate_token(self, token: str, expected_type: str = TOKEN_TYPE_ACCESS) -> dict:
        """
        Validate a JWT token and return its payload.

        Args:
            token: JWT token string
            expected_type: Expected token type (access or refresh)

        Returns:
            dict: Token payload

        Raises:
            InvalidOrExpiredTokenError: If token is invalid or expired
            InvalidTokenPayloadError: If token type doesn't match
        """
        try:
            payload = jwt.decode(
                token, self._get_jwt_secret(), algorithms=[DEFAULT_JWT_ALGORITHM]
            )

            # Verify token type
            token_type = payload.get("type")
            if token_type != expected_type:
                raise InvalidTokenPayloadError(
                    f"Invalid token type. Expected {expected_type}, got {token_type}"
                )

            return payload

        except jwt.ExpiredSignatureError:
            _logger.warning("Token has expired")
            raise InvalidOrExpiredTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            _logger.warning(f"Invalid token: {e}")
            raise InvalidOrExpiredTokenError("Invalid token")

    def get_token_expiry_seconds(self) -> int:
        """Get access token expiry in seconds"""
        return self._get_access_token_expire_minutes() * 60
