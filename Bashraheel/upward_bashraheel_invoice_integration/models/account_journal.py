from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    thirdparty_store_id = fields.Char("Third-Party Store ID", copy=False, help="External identifier for the store/branch")
    thirdparty_store_code = fields.Char("Third-Party Store Code", copy=False)
    thirdparty_store_name = fields.Char("Third-Party Store Name", copy=False)
