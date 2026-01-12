# -*- coding: utf-8 -*-

from odoo import models, api
import logging

from ..core.constants import SERVICE_AUTH
from ..core.exceptions import AuthenticationFailed, UserInactive

_logger = logging.getLogger(__name__)


class AuthService(models.AbstractModel):
    """Service for user authentication"""

    _name = SERVICE_AUTH
    _description = "Bashraheel Auth Service"

    def authenticate_user(self, email: str, password: str) -> dict:
        """
        Authenticate a user by email and password.

        Args:
            email: User's email/login
            password: User's password

        Returns:
            dict: User data including user_id, partner_id, email, name

        Raises:
            AuthenticationFailed: If authentication fails
        """
        try:
            # Use Odoo 18's native authentication with credential dict
            credential = {
                "type": "password",
                "login": email,
                "password": password,
            }
            auth_info = self.env["res.users"].authenticate(
                self.env.cr.dbname, credential, {"interactive": False}
            )

            uid = auth_info.get("uid") if isinstance(auth_info, dict) else auth_info
            if not uid:
                raise AuthenticationFailed("Invalid email or password")

            # Get user details
            user = self.env["res.users"].sudo().browse(uid)
            if not user.exists():
                raise AuthenticationFailed("User not found")

            if not user.active:
                raise UserInactive("User account is inactive")

            return self._build_user_data(user)

        except Exception as e:
            _logger.warning(f"Authentication failed for {email}: {e}")
            if isinstance(e, (AuthenticationFailed, UserInactive)):
                raise
            raise AuthenticationFailed("Invalid email or password")

    def get_user_by_id(self, user_id: int) -> dict:
        """
        Get user data by user ID.

        Args:
            user_id: Odoo user ID

        Returns:
            dict: User data

        Raises:
            AuthenticationFailed: If user not found
        """
        user = self.env["res.users"].sudo().browse(user_id)
        if not user.exists():
            raise AuthenticationFailed("User not found")

        return self._build_user_data(user)

    def validate_user_active(self, user_id: int) -> bool:
        """
        Check if a user is still active.

        Args:
            user_id: Odoo user ID

        Returns:
            bool: True if user is active

        Raises:
            UserInactive: If user is inactive
        """
        user = self.env["res.users"].sudo().browse(user_id)
        if not user.exists() or not user.active:
            raise UserInactive("User account is inactive or does not exist")
        return True

    def _build_user_data(self, user) -> dict:
        """Build user data dictionary from user record"""
        partner = user.partner_id
        return {
            "user_id": user.id,
            "partner_id": partner.id if partner else None,
            "email": user.login,
            "name": user.name,
            "phone": partner.phone if partner else None,
        }
