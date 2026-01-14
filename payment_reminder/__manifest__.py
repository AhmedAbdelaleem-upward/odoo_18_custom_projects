{
    "name": "Payment Reminder (Upward Master & Client)",
    "version": "18.0.1.0.0",
    "summary": "Generic payment reminder with central Upward master and client instances.",
    "category": "Tools",
    "author": "Upward",
    "website": "https://upward.example.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/payment_reminder_security.xml",
        "security/ir.model.access.csv",
        "data/payment_reminder_cron.xml",
        "views/payment_reminder_menu.xml",
        "views/payment_reminder_client_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "payment_reminder/static/src/js/payment_reminder_banner.js",
            "payment_reminder/static/src/xml/payment_reminder_banner.xml",
        ],
    },
    "installable": True,
    "application": False,
}

