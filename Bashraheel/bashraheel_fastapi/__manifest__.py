# -*- coding: utf-8 -*-
{
    'name': "Bashraheel FastAPI Invoice Integration",
    'countries': ['sa'],
    'version': '1.0',
    'summary': "FastAPI endpoints for Bashraheel Invoice Integration with ZATCA",
    'description': """
    This module provides FastAPI REST API endpoints to receive invoice data from
    third-party systems, create invoices in Odoo, and automatically submit them
    to ZATCA for e-invoicing compliance.

    Endpoints:
    - POST /invoice/create - Create invoices from third-party POS
    - POST /invoice/create-return - Create return/refund invoices
    - POST /invoice/report - Query invoice status and ZATCA information
    """,
    'author': "Upward Solutions",
    'website': "https://upward.sa",
    'category': 'Accounting/Localizations/EDI',
    'depends': ['base', 'fastapi', 'bashraheel_invoice_integration'],
    'data': [
        'data/fastapi_endpoint.xml',
    ],
    'demo': [],
    'external_dependencies': {
        'python': ['fastapi', 'pydantic'],
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
