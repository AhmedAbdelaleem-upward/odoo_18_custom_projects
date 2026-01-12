# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.tamara_payment_connector.controllers.main import TamaraController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return the specific processing values.

        Note: self.ensure_one()
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'tamara':
            return res

        _logger.info("Tamara: getting specific processing values for tx %s", self.reference)
        # Base URL for callbacks
        base_url = self.provider_id.get_base_url()
        redirect_url = urls.url_join(base_url, TamaraController._return_url)
        
        # Prepare data for rendering the redirect form
        # In this connector, we will redirect to a controller which handles the actual checkout
        # to either Tamara's real API or our Local Simulation.
        
        simulation_url = urls.url_join(base_url, '/tamara/simulate')
        
        values = {
            'api_url': simulation_url if self.provider_id.tamara_test_mode else 'https://api.tamara.co/checkout',
            'order_reference': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'return_url': redirect_url,
        }
        _logger.info("Tamara: prepared processing values: %s", pprint.pformat(values))
        return values

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return the specific rendering values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'tamara':
            return res
            
        # These values are passed to the qweb template
        return processing_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Tamara data.
        
        pool: payment.transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'tamara' or len(tx) == 1:
            return tx
        
        _logger.info("Tamara: finding tx from notification data: %s", pprint.pformat(notification_data))
        reference = notification_data.get('order_reference')
        if not reference:
             raise ValidationError("Tamara: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'tamara')])
        if not tx:
            raise ValidationError("Tamara: " + _("No transaction found matching reference %s.", reference))
        
        _logger.info("Tamara: found transaction %s", tx.reference)
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the authentication and update the transaction.

        pool: payment.transaction
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'tamara':
            return

        _logger.info("Tamara: processing notification data for tx %s: %s", self.reference, pprint.pformat(notification_data))

        # Handle missing notification data (user left the payment page)
        if not notification_data:
            self._set_canceled(state_message=_("The customer left the payment page."))
            return

        payment_outcome = notification_data.get('payment_outcome')

        # Handle different payment outcomes
        if payment_outcome == 'success':
            _logger.info("Tamara: payment successful, setting done.")
            self._set_done()
        elif payment_outcome == 'cancel':
            _logger.info("Tamara: payment canceled by user.")
            self._set_canceled()
        elif payment_outcome == 'pending':
            _logger.info("Tamara: payment pending.")
            self._set_pending()
        else:
            # Handle error or any other unexpected state
            _logger.warning("Tamara: payment failed or unknown outcome: %s", payment_outcome)
            self._set_error(_("Payment failed. Status: %s", payment_outcome or "Unknown"))

