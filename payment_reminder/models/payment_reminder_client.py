import json
import logging

import requests

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class PaymentReminderClient(models.Model):
    _name = "payment.reminder.client"
    _description = "Payment Reminder Client (Upward Master Side)"
    _rec_name = "name"

    name = fields.Char(required=True)
    database_uuid = fields.Char(string="Database UUID", required=True, index=True, copy=False)
    base_url = fields.Char(string="Client Base URL")
    active_notification = fields.Boolean(string="Enable Notification", default=False)

    notification_start_date = fields.Date(string="Notification Start Date")
    notification_end_date = fields.Date(string="Notification End Date")

    red_threshold_days = fields.Integer(
        string="Red Threshold (days)",
        help="When remaining days to end date is <= this value, the alert will be red.",
        default=0,
    )
    yellow_threshold_days = fields.Integer(
        string="Yellow Threshold (days)",
        help="When remaining days is <= this value and > red threshold, alert will be yellow.",
        default=7,
    )
    green_threshold_days = fields.Integer(
        string="Green Threshold (days)",
        help="When remaining days is <= this value and > yellow threshold, alert will be green.",
        default=30,
    )

    message_green = fields.Text(string="Green Message (Safe)", help="Message to display when in safe period.")
    message_yellow = fields.Text(string="Yellow Message (Warning)", help="Message to display when nearing due date.")
    message_red = fields.Text(string="Red Message (Critical)", help="Message to display when overdue or critical.")
    
    template_green_id = fields.Many2one(
        "payment.reminder.template",
        string="Green Template",
        domain=[("urgent_state", "=", "green")],
        help="Select template for safe period."
    )
    template_yellow_id = fields.Many2one(
        "payment.reminder.template",
        string="Yellow Template",
        domain=[("urgent_state", "=", "yellow")],
        help="Select template for warning period."
    )
    template_red_id = fields.Many2one(
        "payment.reminder.template",
        string="Red Template",
        domain=[("urgent_state", "=", "red")],
        help="Select template for critical period."
    )

    @api.model
    def _default_get_templates(self):
        # Optional: Auto-select standard templates on creation
        # Implementation skipped for brevity, user can select manually.
        pass

    last_seen = fields.Datetime(string="Last Seen", readonly=True)

    _sql_constraints = [
        ("database_uuid_uniq", "unique(database_uuid)", "Database UUID must be unique per client."),
    ]

    @api.model
    def upsert_from_registration(self, vals):
        """Create or update a client record from a registration payload."""
        database_uuid = vals.get("database_uuid")
        if not database_uuid:
            return False
        existing = self.search([("database_uuid", "=", database_uuid)], limit=1)
        vals.setdefault("name", database_uuid)
        vals["last_seen"] = fields.Datetime.now()
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def cron_register_self(self):
        """Cron job executed on ALL databases.

        On client instances, it will (re)register the database on the Upward master.
        On the master itself, it will simply do nothing.
        """
        params = self.env["ir.config_parameter"].sudo()
        role = params.get_param("payment_reminder.role", "client_instance")
        if role != "client_instance":
            return

        master_url = params.get_param("payment_reminder.master_url")
        database_uuid = params.get_param("database.uuid")
        base_url = params.get_param("web.base.url")
        if not master_url or not database_uuid:
            return

        try:
            # Retrieve the shared secret key
            api_key = params.get_param("payment_reminder.api_key", "")
            
            master_url = master_url.rstrip("/")
            register_url = f"{master_url}/payment_reminder/register"
            # Use JSON-RPC format for Odoo type="json" endpoints
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "database_uuid": database_uuid,
                    "base_url": base_url,
                    "name": self.env.cr.dbname,
                },
                "id": None,
            }
            headers = {
                "Content-Type": "application/json",
                "X-Odoo-Payment-Reminder-Secret": api_key,
            }
            requests.post(register_url, json=payload, headers=headers, timeout=5)
        except Exception as e:
            _logger.exception("Error in cron_register_self while registering client: %s", e)

