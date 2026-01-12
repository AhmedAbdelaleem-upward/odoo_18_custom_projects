import logging
from typing import Dict, Any
from odoo import models
from odoo.exceptions import AccessDenied as OdooAccessDenied

from ..core.exceptions import AuthenticationFailed, UserInactive
from ..utils.helpers import build_user_data_dict

_logger = logging.getLogger(__name__)


class AuthService(models.AbstractModel):
    _name = 'simple.auth.service'
    _description = 'Authentication Service for Simple API'

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return user data"""
        try:
            # Use Odoo's native authentication method (Odoo 18 style)
            auth_response = self.env['res.users'].sudo().authenticate(
                db=self.env.cr.dbname,
                credential={
                    "type": "password",
                    "login": email,
                    "password": password,
                },
                user_agent_env=None
            )

            # Odoo 18 returns dict with 'uid'
            if isinstance(auth_response, dict):
                uid = auth_response.get("uid")
            else:
                uid = auth_response

            if not uid:
                _logger.warning("Authentication failed: No UID returned")
                raise AuthenticationFailed()

        except OdooAccessDenied:
            _logger.warning("Authentication failed: Access denied")
            raise AuthenticationFailed()
        except AuthenticationFailed:
            raise
        except Exception as e:
            _logger.exception("Authentication exception: %s", str(e))
            raise AuthenticationFailed()

        user = self.env['res.users'].sudo().browse(uid)
        if not user.exists() or not user.active:
            _logger.warning("User inactive")
            raise UserInactive()

        partner = user.partner_id
        user_data = build_user_data_dict(user, partner)

        _logger.info("Successfully authenticated user (uid: %d)", user.id)
        return user_data

    def get_user_by_id(self, partner_id: int) -> Dict[str, Any]:
        """Get user data by partner ID (used for refresh token)"""
        partner = self.env['res.partner'].sudo().browse(partner_id)
        if not partner.exists():
            _logger.warning("Partner %d not found", partner_id)
            raise UserInactive()

        user = self.env['res.users'].sudo().search(
            [('partner_id', '=', partner.id)],
            limit=1
        )
        if not user or not user.active:
            _logger.warning("No active user found for partner %d", partner_id)
            raise UserInactive()

        user_data = build_user_data_dict(user, partner)
        _logger.info("Retrieved user data for partner %d", partner_id)
        return user_data

    def validate_user_active(self, partner_id: int) -> bool:
        """Check if user is still active"""
        try:
            partner = self.env['res.partner'].sudo().browse(partner_id)
            if not partner.exists():
                return False

            user = self.env['res.users'].sudo().search(
                [('partner_id', '=', partner.id)],
                limit=1
            )
            is_active = user and user.exists() and user.active

            if not is_active:
                _logger.warning("User validation failed for partner %s", partner_id)

            return is_active
        except Exception as e:
            _logger.error(
                "Error validating user for partner %s: %s",
                partner_id,
                str(e)
            )
            return False
