# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TamaraController(http.Controller):
    _return_url = '/payment/tamara/return'
    _webhook_url = '/payment/tamara/webhook'

    @http.route('/tamara/simulate', type='http', auth='public', website=True, csrf=False)
    def tamara_simulate(self, **post):
        """ Render a mock checkout page for Tamara Test Mode. """
        return request.render('tamara_payment_connector.tamara_simulation_page', {
            'order_reference': post.get('order_reference'),
            'amount': post.get('amount'),
            'currency': post.get('currency'),
            'return_url': post.get('return_url'),
        })

    @http.route('/payment/tamara/return', type='http', auth='public', csrf=False, save_session=False)
    def tamara_return(self, **post):
        """ Process the return from Tamara (Real or Simulated). """
        _logger.info('Tamara: entering return handler with data %s', pprint.pformat(post))
        
        _logger.info('Tamara: dispatching to _handle_notification_data')
        request.env['payment.transaction'].sudo()._handle_notification_data('tamara', post)
        
        _logger.info('Tamara: redirecting to status page')
        return request.redirect('/payment/status')

    @http.route('/payment/tamara/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def tamara_webhook(self, **post):
        """ Process Webhook from Tamara. """
        _logger.info("Tamara: processing webhook not implemented for simulation mode")
        return 'OK'

    @http.route('/payment/tamara/process', type='json', auth='public')
    def tamara_process(self, reference, payment_outcome, payment_details, **kwargs):
        """ Process inline form payment simulation. """
        _logger.info('Tamara: processing inline payment for reference %s with outcome %s', reference, payment_outcome)

        notification_data = {
            'order_reference': reference,
            'payment_outcome': payment_outcome,
            'payment_details': payment_details,
        }

        request.env['payment.transaction'].sudo()._handle_notification_data('tamara', notification_data)
        return True
