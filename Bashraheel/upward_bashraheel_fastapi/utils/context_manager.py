# -*- coding: utf-8 -*-

from contextlib import contextmanager
from odoo import api

import logging

_logger = logging.getLogger(__name__)


@contextmanager
def superuser_env(registry, context):
    """
    Context manager that provides a superuser Odoo environment.

    Args:
        registry: Odoo registry
        context: Odoo context dict

    Yields:
        tuple: (env, cursor) where env is the Odoo environment with superuser privileges
    """
    with registry.cursor() as cr:
        try:
            env = api.Environment(cr, 1, context)  # UID 1 = superuser
            yield env, cr
            cr.commit()
        except Exception as e:
            cr.rollback()
            _logger.error(f"Error in superuser_env context: {e}")
            raise
