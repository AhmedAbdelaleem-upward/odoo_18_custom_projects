import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from odoo import models

from ..core.constants import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
    DEFAULT_JWT_SECRET,
    PARAM_KEY_JWT_SECRET,
    PARAM_KEY_ACCESS_EXPIRE_MIN,
    PARAM_KEY_REFRESH_EXPIRE_DAYS,
)

_logger = logging.getLogger(__name__)


class JWTService(models.AbstractModel):
    """Centralized JWT utility service for token generation and validation"""

    _name = 'simple.jwt.service'
    _description = 'JWT Service for Simple API'

    # JWT Configuration - In production, these should be in system parameters
    JWT_SECRET_KEY = DEFAULT_JWT_SECRET
    JWT_ALGORITHM = DEFAULT_JWT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

    def _get_jwt_secret(self):
        """Get JWT secret key from system parameters or default"""
        try:
            return self.env['ir.config_parameter'].sudo().get_param(
                PARAM_KEY_JWT_SECRET,
                default=self.JWT_SECRET_KEY
            )
        except Exception:
            return self.JWT_SECRET_KEY

    def _get_access_token_expire_minutes(self):
        """Get access token expiry from system parameters"""
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(
                PARAM_KEY_ACCESS_EXPIRE_MIN,
                default=str(self.ACCESS_TOKEN_EXPIRE_MINUTES)
            ))
        except Exception:
            return self.ACCESS_TOKEN_EXPIRE_MINUTES

    def _get_refresh_token_expire_days(self):
        """Get refresh token expiry from system parameters"""
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(
                PARAM_KEY_REFRESH_EXPIRE_DAYS,
                default=str(self.REFRESH_TOKEN_EXPIRE_DAYS)
            ))
        except Exception:
            return self.REFRESH_TOKEN_EXPIRE_DAYS

    def generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT access token"""
        try:
            expire_minutes = self._get_access_token_expire_minutes()
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)

            payload = {
                "user_id": user_data.get("uid"),
                "partner_id": user_data.get("id"),
                "email": user_data.get("email"),
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": TOKEN_TYPE_ACCESS
            }

            secret_key = self._get_jwt_secret()
            token = jwt.encode(payload, secret_key, algorithm=self.JWT_ALGORITHM)

            _logger.info("Generated access token for user %s", user_data.get("email"))
            return token

        except Exception as e:
            _logger.error("Error generating access token: %s", str(e))
            raise

    def generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT refresh token"""
        try:
            expire_days = self._get_refresh_token_expire_days()
            expire = datetime.utcnow() + timedelta(days=expire_days)

            payload = {
                "user_id": user_data.get("uid"),
                "partner_id": user_data.get("id"),
                "email": user_data.get("email"),
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": TOKEN_TYPE_REFRESH
            }

            secret_key = self._get_jwt_secret()
            token = jwt.encode(payload, secret_key, algorithm=self.JWT_ALGORITHM)

            _logger.info("Generated refresh token for user %s", user_data.get("email"))
            return token

        except Exception as e:
            _logger.error("Error generating refresh token: %s", str(e))
            raise

    def validate_token(self, token: str, token_type: str = TOKEN_TYPE_ACCESS) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload"""
        try:
            secret_key = self._get_jwt_secret()
            payload = jwt.decode(token, secret_key, algorithms=[self.JWT_ALGORITHM])

            # Check token type
            if payload.get("type") != token_type:
                _logger.warning("Token type mismatch: expected %s, got %s", token_type, payload.get("type"))
                return None

            _logger.info("Successfully validated %s token for user %s", token_type, payload.get("email"))
            return payload

        except jwt.ExpiredSignatureError:
            _logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            _logger.warning("Invalid token: %s", str(e))
            return None
        except Exception as e:
            _logger.error("Error validating token: %s", str(e))
            return None

    def get_token_expiry_seconds(self) -> int:
        """Get access token expiry in seconds"""
        return self._get_access_token_expire_minutes() * 60
