{
    'name': "Bashraheel Invoice Integration With Zatka",
    'countries': ['sa'],
    "version": "18.0.1.0.0",
    'summary': "API to receive invoice data from third-party systems and submit to ZATKA",
    'description': """
    This module provides a REST API to receive invoice data from third-party systems,
    create invoices in Odoo, and automatically submit them to ZATKA for e-invoicing compliance.
    """,
    'author': "Upward Solutions",
    'website': "https://upward.sa",
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_sa_edi'],
    'data': [
        "security/res_groups.xml",
        "security/ir_model_access.xml",
        "security/ir_rule.xml",
        'data/res_partner.xml',
        'data/res_users.xml',
        'data/account_journal_demo.xml',
        'views/invoice.xml',
        'views/account_journal_views.xml',
    ],
    'demo': [
    ],
    'external_dependencies': {
        'python': []
    },
    'license': 'LGPL-3',
}

