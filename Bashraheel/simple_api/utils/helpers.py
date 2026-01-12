"""
Helper utilities for Simple API.

Provides common helper functions for data mapping and formatting.
"""

from typing import Dict, Any


def build_user_data_dict(user, partner) -> Dict[str, Any]:
    """
    Build standardized user data dictionary from Odoo user and partner records.

    Args:
        user: res.users record
        partner: res.partner record

    Returns:
        Dictionary with user data
    """
    # Safe fallback for currency (partner -> partner company -> user company)
    currency = partner.currency_id or \
               partner.company_id.currency_id or \
               user.company_id.currency_id

    return {
        "uid": user.id,
        "id": partner.id,
        "email": user.login,
        "name": partner.name,
        "phone": partner.phone or partner.mobile or None,
        "currency_id": currency.id if currency else None,
        "currency_name": currency.name if currency else None,
    }
