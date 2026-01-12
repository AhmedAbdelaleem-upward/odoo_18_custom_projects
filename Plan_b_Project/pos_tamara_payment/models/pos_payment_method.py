# -*- coding: utf-8 -*-
import json
import logging
import requests
import pprint
from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessDenied

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        """Add Tamara to payment terminal selection"""
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('tamara', 'Tamara')]

    # Tamara Configuration Fields
    tamara_api_token = fields.Char(
        string="API Token",
        help="Tamara API authentication token from merchant dashboard",
        copy=False,
        groups='base.group_erp_manager'
    )
    tamara_test_mode = fields.Boolean(
        string="Test Mode",
        help="Use Tamara sandbox environment for testing",
        default=True,
        groups='base.group_erp_manager'
    )
    tamara_webhook_url = fields.Char(
        string="Webhook URL",
        help="Copy this URL to Tamara merchant dashboard webhook settings",
        compute='_compute_tamara_webhook_url',
        readonly=True,
        store=False
    )
    tamara_latest_response = fields.Char(
        string="Latest Response",
        help="Buffer for latest webhook notification from Tamara",
        copy=False,
        groups='base.group_erp_manager'
    )
    tamara_demo_mode = fields.Boolean(
        string="Demo Mode",
        help="Enable demo/simulation mode for testing without real Tamara credentials. "
             "No actual API calls will be made and webhooks will be simulated.",
        default=False,
        groups='base.group_erp_manager,point_of_sale.group_pos_user'
    )
    tamara_demo_outcome = fields.Selection([
        ('approve', 'Approve Payment'),
        ('decline', 'Decline Payment'),
        ('timeout', 'Timeout (No Response)'),
    ], string="Demo Outcome",
        help="Simulated payment outcome when demo mode is enabled",
        default='approve',
        groups='base.group_erp_manager'
    )
    tamara_demo_delay = fields.Integer(
        string="Demo Delay (seconds)",
        help="Delay before simulated webhook is triggered (1-30 seconds)",
        default=5,
        groups='base.group_erp_manager'
    )

    def _compute_tamara_webhook_url(self):
        """Generate webhook URL for Tamara configuration"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.id:
                record.tamara_webhook_url = f"{base_url}/pos_tamara/notification"
            else:
                record.tamara_webhook_url = False

    @api.constrains('use_payment_terminal', 'tamara_api_token', 'tamara_demo_mode')
    def _check_tamara_credentials(self):
        """Validate that API token is provided when Tamara is selected (unless demo mode)"""
        for record in self:
            if record.use_payment_terminal == 'tamara' and not record.tamara_demo_mode and not record.tamara_api_token:
                raise ValidationError(_('API Token is required for Tamara payment method (or enable Demo Mode for testing)'))

    @api.constrains('tamara_demo_delay')
    def _check_demo_delay(self):
        """Validate demo delay is reasonable"""
        for record in self:
            if record.tamara_demo_delay < 1 or record.tamara_demo_delay > 30:
                raise ValidationError(_('Demo delay must be between 1 and 30 seconds'))

    def _get_tamara_endpoints(self):
        """Get Tamara API endpoints based on test mode"""
        self.ensure_one()
        base_url = 'https://api-sandbox.tamara.co' if self.sudo().tamara_test_mode else 'https://api.tamara.co'

        return {
            'checkout': f'{base_url}/checkout',
            'authorize': f'{base_url}/orders/{{order_id}}/authorise',
            'cancel': f'{base_url}/orders/{{order_id}}/cancel',
            'refund': f'{base_url}/merchants/orders/{{order_id}}/refund',
            'get_order': f'{base_url}/orders/{{order_id}}',
        }

    def _is_write_forbidden(self, fields):
        """Allow webhook to update tamara_latest_response even when POS session is open"""
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - {'tamara_latest_response'})

    def _call_tamara_api(self, endpoint, method='POST', data=None):
        """
        Make authenticated API call to Tamara

        Args:
            endpoint: API endpoint path (e.g., '/checkout')
            method: HTTP method (POST, GET, etc.)
            data: Request payload dictionary

        Returns:
            dict: JSON response from Tamara API or error dict
        """
        self.ensure_one()

        base_url = 'https://api-sandbox.tamara.co' if self.sudo().tamara_test_mode else 'https://api.tamara.co'
        url = f"{base_url}{endpoint}"

        headers = {
            'Authorization': f'Bearer {self.sudo().tamara_api_token}',
            'Content-Type': 'application/json'
        }

        _logger.info('Tamara API request: %s %s', method, endpoint)
        if data:
            _logger.info('Tamara API request data: %s', pprint.pformat(data))

        try:
            response = requests.request(method, url, json=data, headers=headers, timeout=10)

            if response.status_code == 401:
                _logger.error('Tamara API authentication failed')
                return {
                    'error': {
                        'status_code': 401,
                        'message': _('Authentication failed. Please check your Tamara API token.')
                    }
                }

            # Parse JSON response if available
            if response.text:
                result = response.json()
                _logger.info('Tamara API response: %s', pprint.pformat(result))
                return result
            else:
                return {'success': True, 'status_code': response.status_code}

        except requests.exceptions.Timeout:
            _logger.error('Tamara API request timeout')
            return {'error': {'message': _('Request timeout. Please try again.')}}
        except requests.exceptions.RequestException as e:
            _logger.exception('Tamara API request failed: %s', str(e))
            return {'error': {'message': _('Connection error. Please check your internet connection.')}}
        except json.JSONDecodeError as e:
            _logger.exception('Tamara API response parsing failed: %s', str(e))
            return {'error': {'message': _('Invalid response from Tamara.')}}

    def _simulate_tamara_checkout(self, data):
        """
        Simulate Tamara checkout response for demo mode
        Returns fake data matching Tamara's API structure
        """
        self.ensure_one()
        import uuid
        import time

        # Encode current timestamp in order_id for polling logic
        # Format: DEMO-{timestamp}-{random}
        current_time = int(time.time())
        fake_order_id = f"DEMO-{current_time}-{uuid.uuid4().hex[:8]}"
        fake_checkout_url = f"https://demo.tamara.co/checkout/{fake_order_id}"

        _logger.info('DEMO MODE: Simulating Tamara checkout. Order ID: %s', fake_order_id)

        # We no longer use Cron job. The polling mechanism will check the timestamp.
        
        return {
            'order_id': fake_order_id,
            'checkout_url': fake_checkout_url,
            'status': 'initiated',
            'demo_mode': True
        }

    def proxy_tamara_poll(self, data):
        """
        Poll Tamara payment status
        RPC method called from POS frontend
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        order_id = data.get('order_id')
        if not order_id:
            return {'error': {'message': _('Order ID is required')}}

        _logger.info("Polling status for order: %s", order_id)

        # Check if demo mode - simulate polling logic using timestamp
        if self.sudo().tamara_demo_mode:
            import time
            
            # Check if this is a time-encoded demo order
            if order_id.startswith('DEMO-'):
                try:
                    parts = order_id.split('-')
                    # Format: DEMO-{timestamp}-{random}
                    if len(parts) >= 3:
                        start_time = int(parts[1])
                        current_time = int(time.time())
                        elapsed = current_time - start_time
                        
                        delay = self.tamara_demo_delay or 5
                        
                        if elapsed >= delay:
                            # Time passed! Return final status
                            status = 'approved' if self.tamara_demo_outcome == 'approve' else 'declined'
                            if self.tamara_demo_outcome == 'timeout':
                                return {'status': 'initiated', 'demo_mode': True}

                            return {
                                'status': status,
                                'transaction_id': f'DEMO-TXN-{order_id}',
                                'payment_type': 'PAY_BY_INSTALMENTS',
                                'total_amount': {'amount': 100.0, 'currency': 'SAR'},
                                'demo_mode': True
                            }
                except (ValueError, IndexError):
                    _logger.warning("Failed to parse demo order timestamp: %s", order_id)
            
            # If not ready yet or parsing failed
            return {'status': 'initiated', 'demo_mode': True}

        # Real Mode: Call Tamara API
        endpoint = f"/orders/{order_id}"
        response = self.sudo()._call_tamara_api(endpoint, 'GET')
        
        return response

    def proxy_tamara_checkout(self, data):
        """
        Create Tamara checkout session and send SMS payment link
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        _logger.info('Creating Tamara checkout session for order: %s', data.get('order_reference'))

        # Check if demo mode - simulate checkout
        if self.sudo().tamara_demo_mode:
            return self.sudo()._simulate_tamara_checkout(data)

        # Build Tamara checkout request
        checkout_data = {
            'order_reference_id': data['order_reference'],
            'total_amount': {
                'amount': data['amount'],
                'currency': data['currency']
            },
            'description': f"POS Order {data['order_reference']}",
            'country_code': 'SA',  # Default to Saudi Arabia
            'payment_type': 'PAY_BY_INSTALMENTS',
            'items': [{
                'name': 'POS Order Items',
                'type': 'Physical',
                'reference_id': data['order_reference'],
                'sku': 'POS-ORDER',
                'quantity': 1,
                'unit_price': {
                    'amount': data['amount'],
                    'currency': data['currency']
                },
                'total_amount': {
                    'amount': data['amount'],
                    'currency': data['currency']
                }
            }],
            'consumer': {
                'first_name': 'Customer',
                'last_name': 'POS',
                'phone_number': data['phone_number'],
                'email': 'customer@pos.local'
            },
            'merchant_url': {
                'success': f"{self.get_base_url()}/payment/success",
                'failure': f"{self.get_base_url()}/payment/failure",
                'cancel': f"{self.get_base_url()}/payment/cancel",
                'notification': f"{self.get_base_url()}/pos_tamara/notification"
            }
        }

        response = self.sudo()._call_tamara_api('/checkout', 'POST', checkout_data)

        if 'error' in response:
            return response

        return {
            'order_id': response.get('order_id'),
            'checkout_url': response.get('checkout_url'),
            'status': response.get('status')
        }

    def _trigger_demo_webhook(self, order_reference, fake_order_id, cron_id=None):
        """
        LEGACY: This method is kept to handle 'zombie' cron jobs from the previous version.
        It allows the sticky cron jobs to execute and delete themselves without error.
        """
        _logger.info("LEGACY: Cleaning up zombie cron job for order %s", fake_order_id)
        if cron_id:
            try:
                self.env['ir.cron'].sudo().browse(cron_id).unlink()
            except Exception:
                pass
        return

    def proxy_tamara_cancel(self, data):
        """
        Cancel Tamara payment

        RPC method called from POS frontend

        Args:
            data: dict with 'order_id' key

        Returns:
            dict: Response from Tamara or error dict
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        order_id = data.get('order_id')
        if not order_id:
            return {'error': {'message': _('Order ID is required')}}

        _logger.info('Cancelling Tamara payment for order: %s', order_id)

        endpoint = f"/orders/{order_id}/cancel"
        response = self.sudo()._call_tamara_api(endpoint, 'POST', {})

        return response

    def proxy_tamara_refund(self, data):
        """
        Process refund for Tamara payment

        RPC method called from POS frontend

        Args:
            data: dict with keys:
                - order_id: Original Tamara order ID
                - total_amount: Refund amount
                - comment: Reason for refund

        Returns:
            dict: Response from Tamara or error dict
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        order_id = data.get('order_id')
        if not order_id:
            return {'error': {'message': _('Order ID is required')}}

        _logger.info('Processing Tamara refund for order: %s, amount: %s', order_id, data.get('total_amount'))

        # Check if demo mode - simulate success
        if self.sudo().tamara_demo_mode:
            _logger.info('DEMO MODE: Simulating refund approval for order: %s', order_id)
            return {
                'refund_id': f'DEMO-REFUND-{order_id}',
                'status': 'approved',
                'demo_mode': True
            }

        refund_data = {
            'total_amount': {
                'amount': data['total_amount'],
                'currency': data.get('currency', 'SAR')
            },
            'comment': data.get('comment', 'POS Refund')
        }

        endpoint = f"/merchants/orders/{order_id}/refund"
        response = self.sudo()._call_tamara_api(endpoint, 'POST', refund_data)

        return response

    def get_latest_tamara_status(self):
        """
        Fetch latest webhook response

        RPC method called from POS frontend for polling

        Returns:
            dict: Latest webhook notification or False
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        latest_response = self.sudo().tamara_latest_response
        latest_response = json.loads(latest_response) if latest_response else False
        return latest_response

    def proxy_tamara_poll(self, data):
        """
        Poll Tamara payment status
        
        RPC method called from POS frontend
        
        Args:
            data: dict with 'order_id'
            
        Returns:
            dict: {
                'status': 'approved' | 'declined' | 'pending' | ...,
                'transaction_id': str,
                ...
            }
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        order_id = data.get('order_id')
        if not order_id:
            return {'error': {'message': _('Order ID is required')}}

        # Check if demo mode - simulate polling logic with state management
        if self.sudo().tamara_demo_mode:
            _logger.info('DEMO MODE: Polling payment status for order: %s', order_id)

            # First check if we already have a completed response
            latest = self.sudo().tamara_latest_response
            if latest:
                try:
                    resp = json.loads(latest)
                    if resp.get('order_id') == order_id:
                        _logger.info('DEMO MODE: Found existing response for order: %s', order_id)
                        return resp
                except:
                    pass

            # If timeout outcome configured, keep returning pending
            if self.tamara_demo_outcome == 'timeout':
                _logger.info('DEMO MODE: Timeout scenario - returning pending')
                return {'status': 'pending', 'demo_mode': True}

            # Otherwise simulate instant approval/decline (polling fallback)
            # This ensures payment works even if cron fails
            status = 'approved' if self.tamara_demo_outcome == 'approve' else 'declined'
            fake_order_id = order_id.split('--')[0] if '--' in order_id else order_id

            webhook_data = {
                'order_id': order_id,
                'status': status,
                'transaction_id': f'DEMO-TXN-{fake_order_id[:12]}',
                'payment_type': 'PAY_BY_INSTALMENTS',
                'total_amount': {
                    'amount': 100.00,
                    'currency': 'SAR'
                },
                'demo_mode': True
            }

            _logger.info('DEMO MODE: Polling returned %s status', status)
            return webhook_data

        # Real Mode: Call Tamara API
        endpoint = f"/orders/{order_id}"
        response = self.sudo()._call_tamara_api(endpoint, 'GET')
        
        return response
