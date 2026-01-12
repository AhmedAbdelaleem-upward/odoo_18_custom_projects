# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tamara Payment Connector',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider connector for Tamara.",
    'description': " ",  # Non-functional description
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/tamara_templates.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'data/tamara_correction.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tamara_payment_connector/static/src/js/payment_form.js',
        ],
    },
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
