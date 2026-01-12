import logging
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from odoo import fields, models

from ..routers.auth_router import create_auth_router
from ..routers.product_router import create_product_router

_logger = logging.getLogger(__name__)


class SimpleAPIEndpoint(models.Model):
    """Main FastAPI Endpoint for Simple API"""

    _inherit = "fastapi.endpoint"

    def _get_fastapi_routers(self):
        """Return all FastAPI routers for Simple API"""
        routers = super()._get_fastapi_routers()

        if self.app == "simple_api":
            # Capture registry/uid/context for router factories
            registry = self.env.registry
            uid = self.env.uid
            context = dict(self.env.context or {})

            # Create routers using factory pattern
            auth_router = create_auth_router(registry, uid, context)
            product_router = create_product_router(registry, uid, context)

            routers.extend([
                auth_router,
                product_router,
            ])

        return routers

    def _get_fastapi_app_middlewares(self):
        """Add CORS middleware"""
        middlewares = super()._get_fastapi_app_middlewares()

        if self.app == "simple_api":
            origins = ["http://localhost:3000"]
            middlewares.append(
                Middleware(
                    CORSMiddleware,
                    allow_origins=origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            )

        return middlewares


class FastapiEndpoint(models.Model):
    """Extend fastapi.endpoint to add Simple API application"""

    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[("simple_api", "Simple API")],
        ondelete={"simple_api": "cascade"},
    )
