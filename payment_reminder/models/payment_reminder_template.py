from odoo import fields, models


class PaymentReminderTemplate(models.Model):
    _name = "payment.reminder.template"
    _description = "Payment Reminder Message Template"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    body = fields.Text(required=True, translate=True, help="Use {days} as a placeholder for remaining days.")
    urgent_state = fields.Selection(
        [
            ("green", "Green (Safe)"),
            ("yellow", "Yellow (Warning)"),
            ("red", "Red (Critical)"),
        ],
        string="Urgency State",
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
