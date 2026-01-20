import logging
import time
import psycopg2

from odoo import models, fields, _, api
from datetime import datetime, timezone, timedelta
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY as CONCURRENCY_ERRORS

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    thirdparty_invoice_no = fields.Char(string='Third-Party Invoice Number', copy=False, readonly=False, index=True)
    thirdparty_sa_confirmation_datetime = fields.Datetime(string='Third-Party Confirmation Date', readonly=False, copy=False)
    thirdparty_store_id = fields.Char(string='Third-Party Store ID', copy=False, help="Identifier for the source store/branch from the third-party system")

    _sql_constraints = [
        ('thirdparty_invoice_no_uniq', 'unique (thirdparty_invoice_no)', 'Third-Party Invoice Number must be unique'),
    ]

    @api.model
    def _prepare_zatka_invoice(self, vals):
        """
        Process a batch of invoices from third-party POS system.

        This method receives invoice data from external systems, validates and creates
        invoices in Odoo, then submits them to ZATCA for e-invoicing compliance.

        Args:
            vals (dict): Request data containing:
                - invoiceList (list): List of invoice dictionaries to process

        Returns:
            dict: Response with structure:
                - status (str): "success" or "error"
                - data (list): List of individual invoice responses
                - message (str): Error message if status is "error"

        Example:
            {
                "status": "success",
                "data": [
                    {"status": "success", "data": {"id": 123, "qr_code": "...", "odoo_invoice_no": "INV/001"}},
                    {"status": "error", "message": "Invalid date format"}
                ]
            }
        """
        _logger.info("Starting invoice creation batch with %d invoices", len(vals.get('invoiceList', [])))
        response_list = []
        invoiceList = vals.get('invoiceList', [])

        if not invoiceList:
            _logger.warning("Empty invoice list received")
            return {"status": "error", "message": "Invoice list is empty"}

        for invoice_request in invoiceList:
            invoice_no = invoice_request.get('invoiceNo', 'Unknown')
            _logger.info("Processing invoice: %s", invoice_no)
            invoice_return = self._prepare_single_invoice(invoice_request)
            response_list.append(invoice_return)

            if invoice_return.get('status') == 'success':
                _logger.info("Invoice %s created successfully with ID: %s",
                           invoice_no, invoice_return.get('data', {}).get('id'))
            else:
                _logger.error("Invoice %s creation failed: %s",
                            invoice_no, invoice_return.get('message'))

        return {"status": "success", "data": response_list}


    @api.model
    def _report_odoo_invoices(self, vals):
        """
        Retrieve invoices for a specific store and date.

        This method is used by third-party systems to query invoices that were
        created in Odoo, including their ZATCA submission status.

        Args:
            vals (dict): Request data containing:
                - store_id (str): Third-party store identifier
                - date (str): Invoice date in YYYY-MM-DD format

        Returns:
            dict: Response with structure:
                - status (str): "success" or "error"
                - data (list): List of invoice records with fields:
                    - odoo_invoice_id (int): Odoo invoice ID
                    - odoo_invoice_no (str): Odoo invoice number
                    - thirdparty_invoice_no (str): Third-party invoice number
                    - gross_amount (float): Amount before tax
                    - net_amount (float): Total amount including tax
                    - tax_amount (float): Tax amount
                    - invoice_date (date): Invoice date
                    - l10n_sa_confirmation_datetime (datetime): ZATCA confirmation time
                    - invoice_odoo_status (str): Odoo invoice state
                    - invoice_zatka_status (str): ZATCA EDI state
                    - qr_code (str): ZATCA QR code
                    - store_id (str): Store identifier
                - message (str): Error message if status is "error"
        """
        store_id = vals.get('store_id')
        date = vals.get('date')

        _logger.info("Reporting invoices for store_id: %s, date: %s", store_id, date)

        if not store_id:
            _logger.warning("Report request missing store_id")
            return {"status": "error", "message": "Store ID is required"}
        if not date:
            _logger.warning("Report request missing date")
            return {"status": "error", "message": "Date is required"}

        journal = self.env['account.journal']
        journal = journal.search([('thirdparty_store_id', '=', store_id)], limit=1)
        if not journal.exists():
            _logger.error("No journal found for store_id: %s", store_id)
            return {"status": "error", "message": "No Store Found"}

        date = fields.Date.to_date(date)
        read_fields = ['name', 'thirdparty_invoice_no', 'amount_untaxed',
                       'amount_total', 'amount_tax', 'invoice_date',
                       'l10n_sa_confirmation_datetime', 'state', 'edi_state',
                       'l10n_sa_qr_code_str']
        lst_invoices = self.search_read([('journal_id', '=', journal.id), ('invoice_date', '=', date)],
                                        read_fields)

        if lst_invoices:
            lst_invoices = [{'odoo_invoice_id': invoice['id'], 'odoo_invoice_no': invoice['name'] or "",
                             'thirdparty_invoice_no': invoice['thirdparty_invoice_no'] or "",
                             'gross_amount': invoice['amount_untaxed'], 'net_amount': invoice['amount_total'],
                             'tax_amount': invoice['amount_tax'], 'invoice_date': invoice['invoice_date'],
                             'l10n_sa_confirmation_datetime': invoice['l10n_sa_confirmation_datetime'],
                             'invoice_odoo_status': invoice['state'], 'invoice_zatka_status': invoice['edi_state'],
                             'qr_code': invoice['l10n_sa_qr_code_str'], 'store_id': store_id
                             }
                            for invoice in lst_invoices]
            _logger.info("Found %d invoices for store_id: %s, date: %s", len(lst_invoices), store_id, date)
        else:
            _logger.info("No invoices found for store_id: %s, date: %s", store_id, date)
            lst_invoices = []

        return {"status": "success", "data": lst_invoices}

    def _get_default_partner(self):
        """Get or create the default Bashraheel partner for all invoices."""
        # Try to find existing default partner
        default_partner = self.env.ref('bashraheel_invoice_integration.res_partner_bashraheel_default', raise_if_not_found=False)
        
        if not default_partner:
            # Create default partner if it doesn't exist
            default_partner = self.env['res.partner'].sudo().create({
                'name': 'Bashraheel Partner',
                'company_type': 'company',
                'country_id': self.env.ref('base.sa').id,
            })
        
        return default_partner

    def _validate_invoice_line(self, line, invoice_no):
        """
        Validate a single invoice line item.

        Args:
            line (dict): Invoice line data
            invoice_no (str): Invoice number for logging

        Returns:
            dict or None: Error response if validation fails, None if valid
        """
        skuCode = line.get('skuCode', '').strip()
        if not skuCode:
            _logger.error("Invoice %s: Empty SKU code in line item", invoice_no)
            return {"status": "error", "message": "SKU code is required for all line items"}

        try:
            qty = float(line.get('qty', 0))
            if qty <= 0:
                _logger.error("Invoice %s: Invalid quantity %s for SKU %s", invoice_no, qty, skuCode)
                return {"status": "error", "message": f"Quantity must be greater than 0 for SKU {skuCode}"}
        except (ValueError, TypeError):
            _logger.error("Invoice %s: Invalid quantity type for SKU %s", invoice_no, skuCode)
            return {"status": "error", "message": f"Invalid quantity for SKU {skuCode}"}

        try:
            price = float(line.get('sellingPrice', 0))
            if price < 0:
                _logger.error("Invoice %s: Negative price %s for SKU %s", invoice_no, price, skuCode)
                return {"status": "error", "message": f"Price cannot be negative for SKU {skuCode}"}
        except (ValueError, TypeError):
            _logger.error("Invoice %s: Invalid price type for SKU %s", invoice_no, skuCode)
            return {"status": "error", "message": f"Invalid price for SKU {skuCode}"}

        try:
            discount = float(line.get('discount', 0))
            if discount < 0 or discount > 100:
                _logger.error("Invoice %s: Invalid discount %s for SKU %s", invoice_no, discount, skuCode)
                return {"status": "error", "message": f"Discount must be between 0 and 100 for SKU {skuCode}"}
        except (ValueError, TypeError):
            _logger.error("Invoice %s: Invalid discount type for SKU %s", invoice_no, skuCode)
            return {"status": "error", "message": f"Invalid discount for SKU {skuCode}"}

        return None

    def _prepare_single_invoice(self, dct_invoice):
        """
        Process and create a single invoice from third-party data.

        This method validates invoice data, creates the invoice in Odoo,
        posts it, and submits it to ZATCA for e-invoicing compliance.

        Args:
            dct_invoice (dict): Invoice data containing:
                - invoiceNo (str): Unique invoice number (required)
                - move_type (str): 'out_invoice' or 'out_refund' (required)
                - documentDate (str): Invoice date in YYYY-MM-DD format (required)
                - thirdparty_sa_confirmation_datetime (str): Confirmation datetime in YYYY-MM-DD HH:MM:SS format (required)
                - store (dict): Store information with 'id' field (required for out_invoice)
                - lines (list): Invoice line items (required, non-empty)
                    Each line contains:
                    - skuCode (str): Product SKU (required)
                    - skuid (str): Optional SKU ID
                    - qty (float): Quantity (required, > 0)
                    - sellingPrice (float): Unit price (required, >= 0)
                    - discount (float): Discount percentage (0-100)
                - main_invoiceNo (str): Original invoice number (required for refunds)
                - out_refund_type (str): 'full' or 'partial' (required for refunds)

        Returns:
            dict: Response with structure:
                - status (str): "success" or "error"
                - data (dict): Success data containing:
                    - id (int): Created invoice ID
                    - qr_code (str): ZATCA QR code
                    - odoo_invoice_no (str): Odoo invoice number
                - message (str): Error message if status is "error"

        Note:
            - Future dates are automatically adjusted to today
            - Timezone offset of -3 hours is applied to confirmation datetime
            - Invoice is automatically posted and submitted to ZATCA
        """
        store_dct = dct_invoice.get('store', {})
        invoice_created = self.env['account.move']
        invoiceNo = dct_invoice.get("invoiceNo", "")
        documentDate = dct_invoice.get('documentDate', "")
        thirdparty_sa_confirmation_datetime = dct_invoice.get('thirdparty_sa_confirmation_datetime', "")
        move_type = dct_invoice.get('move_type')
        invoice_lines = dct_invoice.get('lines', [])
        invoice_line_ids = []

        _logger.debug("Validating invoice %s of type %s", invoiceNo, move_type)

        # Validate move_type
        if move_type not in ['out_invoice', 'out_refund']:
            _logger.error("Invoice %s: Invalid move_type %s", invoiceNo, move_type)
            return {"status": "error", "message": f"Invalid move_type. Must be 'out_invoice' or 'out_refund'"}

        # Validate invoice lines are not empty
        if not invoice_lines:
            _logger.error("Invoice %s: No line items provided", invoiceNo)
            return {"status": "error", "message": "Invoice must have at least one line item"}

        try:
            documentDate = fields.Date.to_date(documentDate)
            if documentDate > fields.Date.today():
                _logger.warning("Invoice %s: Future date %s adjusted to today", invoiceNo, documentDate)
                documentDate = fields.Date.today()

        except ValueError:
            _logger.error("Invoice %s: Invalid date format", invoiceNo)
            return {"status": "error", "message": "Invalid date format"}

        if not store_dct and move_type == 'out_invoice':
            _logger.error("Invoice %s: Missing store information", invoiceNo)
            return {"status": "error", "message": "Store Dict is required"}

        customer_data = self._get_default_partner()
        _logger.debug("Invoice %s: Using partner %s", invoiceNo, customer_data.name)

        journal_store = self._prepare_journal_store(store_dct)
        if not journal_store and move_type == 'out_invoice':
            _logger.error("Invoice %s: Journal not found for store %s", invoiceNo, store_dct.get('id'))
            return {"status": "error", "message": "Store Is Wrong , Please Define in Odoo First"}

        if journal_store:
            _logger.debug("Invoice %s: Using journal %s", invoiceNo, journal_store.name)

        if not invoiceNo:
            _logger.error("Invoice creation failed: Missing invoice number")
            return {"status": "error", "message": "InvoiceNo is required"}

        else:
            invoice_count = invoice_created.search_count([('thirdparty_invoice_no', '=', invoiceNo)])
            if invoice_count:
                _logger.warning("Invoice %s: Duplicate invoice number detected", invoiceNo)
                return {"status": "error", "message": f"InvoiceNo ({invoiceNo}) already exists"}

        if not thirdparty_sa_confirmation_datetime:
            _logger.error("Invoice %s: Missing confirmation datetime", invoiceNo)
            return {"status": "error", "message": "Confirmation DateTime Is required"}
        else:
            try:
                thirdparty_sa_confirmation_datetime = datetime.strptime(thirdparty_sa_confirmation_datetime, "%Y-%m-%d %H:%M:%S")
                three_hours = timedelta(hours=3)
                thirdparty_sa_confirmation_datetime = thirdparty_sa_confirmation_datetime - three_hours
                thirdparty_sa_confirmation_datetime = thirdparty_sa_confirmation_datetime.strftime("%Y-%m-%d %H:%M:%S")
                _logger.debug("Invoice %s: Confirmation datetime adjusted for timezone", invoiceNo)
            except ValueError:
                _logger.error("Invoice %s: Invalid confirmation datetime format", invoiceNo)
                msg = "Error: Invalid datetime format. Please check the input string."
                return {"status": "error", "message": msg}

        try:
            with self.env.cr.savepoint():
                _logger.debug("Invoice %s: Processing %d line items", invoiceNo, len(invoice_lines))
                
                # income_account logic removed as we use product_id now

                for invoice_line in invoice_lines:
                    # Validate each line item
                    validation_error = self._validate_invoice_line(invoice_line, invoiceNo)
                    if validation_error:
                        return validation_error

                    skuid = invoice_line.get('skuid', "")
                    skuCode = invoice_line.get('skuCode', "").strip()
                    sellingPrice = float(invoice_line.get('sellingPrice', 0))
                    qty = float(invoice_line.get('qty', 0))
                    discount = float(invoice_line.get('discount', 0))

                    # Product Lookup
                    product = self.env['product.product'].search([('default_code', '=', skuCode)], limit=1)
                    if not product:
                        _logger.error("Invoice %s: Product with SKU %s not found", invoiceNo, skuCode)
                        return {"status": "error", "message": f"Product with SKU {skuCode} not found"}
                    
                    line_vals = {
                        "thirdparty_sku_id": skuid, 
                        "name": skuCode, 
                        "product_id": product.id,
                        "quantity": qty,
                        "price_unit": sellingPrice, 
                        "discount": discount,
                    }
                    invoice_line_ids.append((0, 0, line_vals))
                    
                if move_type == 'out_invoice':
                    _logger.info("Invoice %s: Creating customer invoice", invoiceNo)
                    invoice_data = {
                        "partner_id": customer_data.id,
                        "journal_id": journal_store.id,
                        "move_type": move_type,
                        "invoice_date": documentDate,
                        "thirdparty_sa_confirmation_datetime": thirdparty_sa_confirmation_datetime,
                        "thirdparty_invoice_no": invoiceNo,
                        "invoice_line_ids": invoice_line_ids
                    }
                    invoice_created = self._account_move_out_invoice(invoice_data)
                elif move_type == 'out_refund':
                    main_invoiceNo = dct_invoice.get('main_invoiceNo')
                    out_refund_type = dct_invoice.get('out_refund_type')
                    _logger.info("Invoice %s: Creating refund (%s) for invoice %s", invoiceNo, out_refund_type, main_invoiceNo)
                    if not main_invoiceNo:
                        _logger.error("Invoice %s: Missing main invoice number for refund", invoiceNo)
                        return {"status": "error", "message": "Main Invoice No is required"}
                    if not out_refund_type:
                        _logger.error("Invoice %s: Missing refund type", invoiceNo)
                        return {"status": "error", "message": "Out Refund Type is required"}
                    else:
                        if out_refund_type not in ['full', 'partial']:
                            _logger.error("Invoice %s: Invalid refund type %s", invoiceNo, out_refund_type)
                            return {"status": "error", "message": "Out Refund Type is wrong"}
                    invoice_created = self._account_move_out_refund(journal_store, main_invoiceNo, invoiceNo, out_refund_type,
                                                                    documentDate, thirdparty_sa_confirmation_datetime,
                                                                    invoice_line_ids)
                if not invoice_created.exists():
                    _logger.error("Invoice %s: Failed to create invoice record", invoiceNo)
                    return {"status": "error", "message": f"Error while creating invoice with number ({invoiceNo})"}

                _logger.info("Invoice %s: Posting invoice with ID %s", invoiceNo, invoice_created.id)
                invoice_created.action_post()

                _logger.info("Invoice %s: Submitting to ZATCA", invoiceNo)
                invoice_created.action_process_edi_web_services()

                if invoice_created.edi_state in ['sent', 'to_send']:
                    _logger.info("Invoice %s: ZATCA submission successful (state: %s)", invoiceNo, invoice_created.edi_state)
                else:
                    _logger.warning("Invoice %s: ZATCA submission may have issues (state: %s)", invoiceNo, invoice_created.edi_state)
        except Exception as error:
            if isinstance(error, psycopg2.OperationalError) \
                    and error.pgcode in CONCURRENCY_ERRORS:
                _logger.warning(
                    "Invoice %s: Concurrency error occurred during processing",
                    invoiceNo
                )
                self.env.cr.rollback()
                time.sleep(.1)
                return {"status": "error", "message": "Concurrency error - please retry"}
            else:
                _logger.exception("Invoice %s: Unexpected error during processing", invoiceNo)
                msg = f'Invoice with ref {invoiceNo} failed during processing. Error details: {error}'
                return {"status": "error", "message": msg}

        return {
            "status": "success",
            "data": {
                'id': invoice_created.id,
                'qr_code': invoice_created.l10n_sa_qr_code_str,
                "odoo_invoice_no": invoice_created.name or ""
            },
        }

    def _prepare_journal_store(self, store_dct):
        if not store_dct:
            return False
        store_journal = self.env['account.journal']
        external_pos_store_id = store_dct.get('id')
        store_journal = store_journal.search([('thirdparty_store_id', '=', external_pos_store_id)], limit=1)
        if not store_journal:
            return False
        return store_journal

    def _account_move_out_invoice(self, invoice_data):
        invoice_created = self.env['account.move'].create(invoice_data)
        return invoice_created

    def _get_refund_journal_id(self, journal_store, main_invoice):
        """
        Get the appropriate journal ID for refund creation.

        Args:
            journal_store: Journal record from store data (can be False)
            main_invoice: Original invoice record being refunded

        Returns:
            int: Journal ID to use for refund

        Raises:
            UserError: If no valid journal is found
        """
        if journal_store:
            return journal_store.id

        if not main_invoice:
            raise UserError(_('Main invoice not found'))

        # Try to use main invoice's journal if it has EDI formats
        if main_invoice.journal_id and main_invoice.journal_id.edi_format_ids:
            return main_invoice.journal_id.id

        # Try to find journal by store ID if available
        if main_invoice.thirdparty_store_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('thirdparty_store_id', '=', main_invoice.thirdparty_store_id),
                ('edi_format_ids', '!=', False)
            ], limit=1)
            if journal:
                return journal.id

        raise UserError(_('Please set journal for invoice'))

    def _account_move_out_refund(self, journal_store, main_invoiceNo, invoiceNo, out_refund_type, documentDate,
                                 thirdparty_sa_confirmation_datetime, invoice_line_ids, return_reason='Product issue'):
        invoice_created = self.env['account.move']
        # invoice_previous_period = (fields.Date.today() + timedelta(days=-50)).strftime('%Y-%m-%d')
        domain_thirdparty = [('thirdparty_invoice_no', '=', main_invoiceNo), ('state', '=', 'posted')]
        # Removed date filter to allow refunding older invoices
        main_invoice = self.env['account.move'].search(domain_thirdparty, limit=1)

        if documentDate > fields.Date.today():
            documentDate = fields.Date.today()

        journal_id = self._get_refund_journal_id(journal_store, main_invoice)

        if main_invoice:
            if out_refund_type == 'full':
                invoice_created = self._account_move_out_refund_full(journal_id, main_invoice, return_reason, documentDate, thirdparty_sa_confirmation_datetime,
                                                                      invoiceNo)
            elif out_refund_type == 'partial':
                invoice_created = self._account_move_out_refund_partial(journal_id, main_invoice, invoiceNo, documentDate, thirdparty_sa_confirmation_datetime,
                                                                        invoice_line_ids)

            return invoice_created
        return invoice_created

    def _account_move_out_refund_full(self, journal_id, main_invoice, return_reason, documentDate, thirdparty_sa_confirmation_datetime, invoiceNo):
        move_reversal = self.env['account.move.reversal'] \
            .with_context(active_model='account.move', active_ids=[main_invoice.id]) \
            .create(
            {'journal_id': journal_id,
             'reason': return_reason,
             'date': documentDate
             })
        invoice_created = self.env['account.move'].browse(move_reversal.refund_moves()['res_id'])
        invoice_created.write({
            'thirdparty_invoice_no': invoiceNo,
            'thirdparty_sa_confirmation_datetime': thirdparty_sa_confirmation_datetime
        })
        return invoice_created

    def _account_move_out_refund_partial(self, journal_id, main_invoice, invoiceNo, documentDate, thirdparty_sa_confirmation_datetime,
                                         invoice_line_ids):
        invoice_return = {
            'move_type': 'out_refund',
            'partner_id': main_invoice.partner_id.id,
            'journal_id': journal_id,
            'invoice_date': documentDate,
            'thirdparty_sa_confirmation_datetime': thirdparty_sa_confirmation_datetime,
            'invoice_line_ids': invoice_line_ids,
            'ref': _('Reversal of: %(invoice)s', invoice=main_invoice.name),
            'reversed_entry_id': main_invoice.id,
            'invoice_origin': invoiceNo,
            'thirdparty_invoice_no': invoiceNo
        }
        invoice_created = self.env["account.move"].create(invoice_return)
        return invoice_created

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'SA' and move.is_sale_document():
                if move.thirdparty_sa_confirmation_datetime:
                    _logger.debug("Invoice %s: Setting ZATCA confirmation datetime from third-party system",
                                move.thirdparty_invoice_no or move.name)
                    vals = {'l10n_sa_confirmation_datetime': move.thirdparty_sa_confirmation_datetime}
                    move.write(vals)
        return res
        