# -*- coding: utf-8 -*-
import json
import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosTamaraController(http.Controller):

    @http.route('/pos_tamara/notification', type='json', methods=['POST'], auth='public', csrf=False, save_session=False)
    def notification(self):
        """
        Handle webhook notifications from Tamara payment gateway

        This endpoint receives payment status updates from Tamara and forwards them
        to the POS frontend via WebSocket notifications.

        Expected webhook payload from Tamara:
        {
            'order_id': 'uuid--session_id',
            'status': 'approved' | 'declined' | 'expired' | 'failed',
            'transaction_id': 'tamara_transaction_id',
            ... other fields
        }
        """
        try:
            data = json.loads(request.httprequest.data)
            _logger.info('Tamara webhook notification received:\n%s', pprint.pformat(data))
        except (json.JSONDecodeError, AttributeError) as e:
            _logger.error('Failed to parse Tamara webhook data: %s', str(e))
            return request.make_json_response({'error': 'Invalid JSON'}, status=400)

        # Extract critical fields from webhook
        order_id = data.get('order_id')
        status = data.get('status')

        if not order_id:
            _logger.warning('Tamara webhook missing order_id')
            return request.make_json_response({'error': 'Missing order_id'}, status=400)

        _logger.info('Processing Tamara payment notification for order: %s, status: %s', order_id, status)

        # Extract POS session from order_id (format: uuid--session_id)
        pos_session = self._extract_pos_session(order_id)
        if not pos_session:
            _logger.warning('Could not find POS session for order_id: %s', order_id)
            return request.make_json_response({'error': 'Invalid order_id format'}, status=400)

        # Find Tamara payment method for this POS config
        payment_method = self._find_payment_method(pos_session)
        if not payment_method:
            _logger.warning('No Tamara payment method found for POS session: %s', pos_session.id)
            return request.make_json_response({'error': 'Payment method not found'}, status=404)

        # Store latest response for potential polling fallback
        payment_method.sudo().tamara_latest_response = json.dumps(data)

        # Prepare payload for WebSocket notification
        notification_payload = {
            'config_id': pos_session.config_id.id,
            'order_id': order_id,
            'status': status,
            'transaction_id': data.get('transaction_id'),
            'payment_type': data.get('payment_type'),
            'amount': data.get('total_amount', {}).get('amount'),
            'currency': data.get('total_amount', {}).get('currency'),
        }

        # Notify POS frontend via WebSocket
        try:
            pos_session.config_id._notify('TAMARA_LATEST_RESPONSE', notification_payload)
            _logger.info('Sent WebSocket notification to POS config: %s', pos_session.config_id.id)
        except Exception as e:
            _logger.exception('Failed to send WebSocket notification: %s', str(e))

        return request.make_json_response({'success': True})

    def _extract_pos_session(self, order_id):
        """
        Extract POS session from order_id

        Args:
            order_id: Order reference in format 'uuid--session_id'

        Returns:
            pos.session record or None
        """
        try:
            # Order ID format: "uuid--session_id"
            if '--' not in order_id:
                return None

            parts = order_id.split('--')
            if len(parts) != 2:
                return None

            session_id = int(parts[1])
            pos_session = request.env['pos.session'].sudo().browse(session_id)

            if not pos_session.exists():
                return None

            return pos_session

        except (ValueError, IndexError) as e:
            _logger.error('Failed to extract session from order_id %s: %s', order_id, str(e))
            return None

    def _find_payment_method(self, pos_session):
        """
        Find Tamara payment method for given POS session

        Args:
            pos_session: pos.session record

        Returns:
            pos.payment.method record or None
        """
        try:
            payment_method = request.env['pos.payment.method'].sudo().search([
                ('use_payment_terminal', '=', 'tamara'),
                ('id', 'in', pos_session.config_id.payment_method_ids.ids)
            ], limit=1)

            return payment_method

        except Exception as e:
            _logger.exception('Failed to find payment method: %s', str(e))
            return None
