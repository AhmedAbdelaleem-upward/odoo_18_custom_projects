"""
Context manager utilities for Simple API.

Provides context managers for Odoo environment management.
"""

import logging
from contextlib import contextmanager
from typing import Tuple, Any
from odoo import api

_logger = logging.getLogger(__name__)


@contextmanager
def user_env(registry, context, auth_context) -> Tuple[api.Environment, int, Any]:
    """
    Context manager to yield an Odoo Environment bound to the authenticated user.

    Args:
        registry: Odoo registry
        context: Odoo context dict
        auth_context: Authentication context from JWT (contains user_id, partner_id)

    Yields:
        Tuple of (env, partner_id, cr)

    Usage:
        with user_env(registry, context, auth) as (env, partner_id, cr):
            service = env['simple.partner.service']
            result = service.get_partners(partner_id, limit=10)
    """
    with registry.cursor() as cr:
        user_id = auth_context['user_id']
        partner_id = auth_context.get('partner_id')

        temp_env = api.Environment(cr, user_id, context)

        if not partner_id:
            # Fallback if missing from token
            partner_id = temp_env.user.partner_id.id

        yield temp_env, partner_id, cr
