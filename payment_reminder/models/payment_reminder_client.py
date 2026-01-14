from odoo import api, fields, models


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

    message = fields.Text(string="Client Message")

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

