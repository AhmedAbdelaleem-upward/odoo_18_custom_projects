# -*- coding: utf-8 -*-

from odoo import models, fields, api
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import logging

from ..routers.invoice_router import create_invoice_router
from ..routers.auth_router import create_auth_router

_logger = logging.getLogger(__name__)


class BashraeelFastapiEndpoint(models.Model):
    """
    FastAPI endpoint model for Bashraheel Invoice Integration.

    This model extends the base fastapi.endpoint to provide
    invoice-related API endpoints.
    """

    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[("bashraheel_invoice", "Bashraheel Invoice API")],
        ondelete={"bashraheel_invoice": "cascade"},
    )

    def _get_fastapi_routers(self):
        """
        Return the FastAPI routers for this endpoint.

        Returns routers only when the app type is 'bashraheel_invoice'.
        """
        routers = super()._get_fastapi_routers()

        if self.app == "bashraheel_invoice":
            _logger.info("Loading Bashraheel Invoice FastAPI routers")
            # Add auth router (login/refresh endpoints)
            routers.append(
                create_auth_router(
                    self.env.registry,
                    self.env.uid,
                    self.env.context,
                )
            )
            # Add invoice router (protected endpoints)
            routers.append(
                create_invoice_router(
                    self.env.registry,
                    self.env.uid,
                    self.env.context,
                )
            )

        return routers

    def _get_fastapi_app_middlewares(self):
        """
        Return the FastAPI middlewares for this endpoint.

        Adds CORS middleware for cross-origin requests.
        """
        middlewares = super()._get_fastapi_app_middlewares()

        if self.app == "bashraheel_invoice":
            # Add CORS middleware to allow cross-origin requests
            middlewares.append(
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            )

        return middlewares
