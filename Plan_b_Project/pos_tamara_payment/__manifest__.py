# -*- coding: utf-8 -*-
{
    'name': 'POS Tamara Payment',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate Tamara Buy Now Pay Later payment gateway with Point of Sale',
    'description': """
POS Tamara Payment Integration
================================

This module integrates Tamara payment gateway (Buy Now, Pay Later) with Odoo Point of Sale.

Features:
- SMS-based payment link sent to customers
- Real-time payment status updates via webhook
- Support for payment processing and refunds
- Transaction tracking
- Test mode for development and production mode for live transactions

Configuration:
- Add Tamara API token in payment method settings
- Configure webhook URL in Tamara merchant dashboard
- Enable test mode for sandbox environment
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_tamara_payment/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
