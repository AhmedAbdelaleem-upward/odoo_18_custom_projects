from odoo import api, fields, models


class PaymentReminderSettings(models.TransientModel):
    _inherit = "res.config.settings"

    payment_reminder_role = fields.Selection(
        [
            ("upward_master", "Upward Master"),
            ("client_instance", "Client Instance"),
        ],
        string="Payment Reminder Role",
        default="client_instance",
        help="Define whether this database acts as the central Upward master or as a client.",
    )
    payment_reminder_master_url = fields.Char(
        string="Upward Master Base URL",
        help="Base URL of the Upward master instance, used by client instances for API calls.",
    )
    payment_reminder_api_key = fields.Char(
        string="API Secret Key",
        help="Shared secret key. Must match between Master and Client instances.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        res.update(
            payment_reminder_role=params.get_param(
                "payment_reminder.role", default="client_instance"
            ),
            payment_reminder_master_url=params.get_param(
                "payment_reminder.master_url", default=""
            ),
            payment_reminder_api_key=params.get_param(
                "payment_reminder.api_key", default=""
            ),
        )
        return res

    def set_values(self):
        super().set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("payment_reminder.role", self.payment_reminder_role or "client_instance")
        params.set_param("payment_reminder.master_url", self.payment_reminder_master_url or "")
        params.set_param("payment_reminder.api_key", self.payment_reminder_api_key or "")

