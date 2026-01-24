# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends
from odoo import api

import logging

from ..schemas.invoice_schemas import (
    CreateInvoiceRequest,
    CreateInvoiceResponse,
    ReportInvoicesRequest,
    ReportInvoicesResponse,
)
from ..core.constants import SERVICE_INVOICE
from ..utils.decorators import handle_router_errors
from ..auth.dependencies import create_jwt_auth_dependency, bearer_scheme

# Define dependencies list for protected routes (enables Swagger UI "Authorize" button)
jwt_security = [Depends(bearer_scheme)]

_logger = logging.getLogger(__name__)


def create_invoice_router(registry, uid, context):
    """
    Factory function to create the invoice router with Odoo context.

    Args:
        registry: Odoo registry
        uid: User ID
        context: Odoo context

    Returns:
        APIRouter: FastAPI router with invoice endpoints
    """
    # Create JWT auth dependency
    jwt_auth = create_jwt_auth_dependency(registry, uid, context)

    # Router with JWT security dependency - enables "Authorize" button in Swagger UI
    router = APIRouter(
        prefix="/invoice",
        tags=["Invoice"],
        dependencies=jwt_security,  # All routes in this router require JWT auth
    )

    @router.post(
        "/create",
        response_model=CreateInvoiceResponse,
        summary="Create invoices from third-party POS",
        description="""
Create one or more invoices from third-party POS data and submit to ZATCA.

## Invoice Types
- **out_invoice**: Regular sales invoice
- **out_refund**: Refund/Credit Note (requires `main_invoiceNo` and `out_refund_type`)

## Refund Types
- **partial**: Refund specific items (uses provided `lines`)
- **full**: Full reversal of original invoice (ignores `lines` but requires at least one dummy line)

## Required Fields
| Field | Description |
|-------|-------------|
| invoiceNo | Unique third-party invoice reference |
| move_type | `out_invoice` or `out_refund` |
| documentDate | Invoice date (YYYY-MM-DD) |
| store.id | Store identifier (must exist in Odoo journals) |
| lines | At least one line item |

## Notes
- `thirdparty_sa_confirmation_datetime` is used for ZATCA compliance
- Invoice numbers must be unique across the system
        """,
    )
    @handle_router_errors
    def create_invoices(
        request: CreateInvoiceRequest,
        auth: dict = Depends(jwt_auth),
    ) -> CreateInvoiceResponse:
        """
        Create invoices from third-party POS system.

        This endpoint receives invoice data from external systems (e.g., POS),
        creates the invoices in Odoo, and submits them to ZATCA for e-invoicing.

        Requires JWT Bearer token authentication.
        """
        _logger.info(f"create_invoices endpoint called by user: {auth.get('email')}")

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)  # Superuser
            invoice_service = env[SERVICE_INVOICE]
            result = invoice_service.create_invoices(request.model_dump())
            cr.commit()
            return result

    @router.post(
        "/create-return",
        response_model=CreateInvoiceResponse,
        summary="Create return/refund invoices",
        description="Create return or refund invoices from third-party POS data",
    )
    @handle_router_errors
    def create_return_invoices(
        request: CreateInvoiceRequest,
        auth: dict = Depends(jwt_auth),
    ) -> CreateInvoiceResponse:
        """
        Create return/refund invoices from third-party POS system.

        This endpoint handles refund and return invoices. The invoices in the
        request should have move_type='out_refund' and include main_invoiceNo
        and out_refund_type fields.

        Requires JWT Bearer token authentication.
        """
        _logger.info(f"create_return_invoices endpoint called by user: {auth.get('email')}")

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)  # Superuser
            invoice_service = env[SERVICE_INVOICE]
            result = invoice_service.create_invoices(request.model_dump())
            cr.commit()
            return result

    @router.post(
        "/report",
        response_model=ReportInvoicesResponse,
        summary="Query invoice status",
        description="Query invoices for a specific store and date with ZATCA submission status. Returns response fields: odoo_invoice_id, odoo_invoice_no, thirdparty_invoice_no, gross_amount, net_amount, tax_amount, invoice_odoo_status, invoice_zatka_status, qr_code.",
    )
    @handle_router_errors
    def report_invoices(
        request: ReportInvoicesRequest,
        auth: dict = Depends(jwt_auth),
    ) -> ReportInvoicesResponse:
        """
        Query invoices for a specific store and date.

        Returns invoice details including ZATCA submission status and QR codes.

        Requires JWT Bearer token authentication.
        """
        _logger.info(f"report_invoices endpoint called for store: {request.store_id} by user: {auth.get('email')}")

        with registry.cursor() as cr:
            env = api.Environment(cr, 1, context)  # Superuser
            invoice_service = env[SERVICE_INVOICE]
            result = invoice_service.report_invoices(request.model_dump())
            cr.commit()
            return result

    return router
