# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('tamara', "Tamara")],
        ondelete={'tamara': 'set default'},
    )
    tamara_api_token = fields.Char(
        string="API Token",
        help="The API Token provided by Tamara",
        required_if_provider='tamara',
        groups='base.group_system',
    )
    tamara_test_mode = fields.Boolean(
        string="Test Mode",
        help="Run transactions in the test environment.",
        default=True,
    )

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'tamara':
            supported_currencies = self.env['res.currency'].search([
                ('name', 'in', ['SAR', 'AED', 'KWD', 'BHD', 'OMR', 'QAR']),
            ])
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'tamara':
            return default_codes
        return {'tamara'}
