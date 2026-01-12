# -*- coding: utf-8 -*-
import json
from odoo.http import Controller, request, route
from odoo import SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)

class PureController(Controller):

    @route('/api/create_odoo_invoice', type='json', auth='api_key', methods=['POST'], csrf=False)
    def create_odoo_invoice(self):
        body = json.loads(request.httprequest.data)
        _logger.info("create_odoo_invoice : body data %s " % body)
        env = request.env(su=True)
        invoice_data = env['account.move']._prepare_zatka_invoice(body)
        return invoice_data

    @route('/api/create_odoo_invoice_return_store', type='json', auth='api_key', methods=['POST'], csrf=False)
    def create_odoo_invoice_return_store(self):
        body = json.loads(request.httprequest.data)
        _logger.info("create_odoo_invoice_return_store : body data %s " % body)
        env = request.env(su=True)
        invoice_data = env['account.move']._prepare_zatka_invoice(body)
        return invoice_data

    @route('/api/report_invoices', type='json', auth='api_key', methods=['POST'], csrf=False)
    def report_invoices(self):
        body = json.loads(request.httprequest.data)
        env = request.env(su=True)
        invoice_data = env['account.move']._report_odoo_invoices(body)
        return invoice_data
