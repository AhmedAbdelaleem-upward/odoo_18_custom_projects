# -*- coding: utf-8 -*-

from odoo import models, api
import logging

from ..core.constants import SERVICE_INVOICE

_logger = logging.getLogger(__name__)


class InvoiceService(models.AbstractModel):
    """Service for handling invoice operations via FastAPI"""

    _name = SERVICE_INVOICE
    _description = "Bashraheel Invoice Service for FastAPI"

    def create_invoices(self, invoice_data: dict) -> dict:
        """
        Create invoices from third-party POS data.

        This method delegates to the existing account.move._prepare_zatka_invoice()
        method from upward_bashraheel_invoice_integration module.

        Args:
            invoice_data: Dictionary containing 'invoiceList' with invoice details

        Returns:
            dict: Response with status and created invoice data
        """
        _logger.info(f"FastAPI create_invoices called with data: {invoice_data}")
        return self.env["account.move"]._prepare_zatka_invoice(invoice_data)

    def report_invoices(self, report_data: dict) -> dict:
        """
        Query invoices for a specific store and date.

        This method delegates to the existing account.move._report_odoo_invoices()
        method from upward_bashraheel_invoice_integration module.

        Args:
            report_data: Dictionary containing 'store_id' and 'date'

        Returns:
            dict: Response with status and invoice report data
        """
        _logger.info(f"FastAPI report_invoices called with data: {report_data}")
        return self.env["account.move"]._report_odoo_invoices(report_data)
