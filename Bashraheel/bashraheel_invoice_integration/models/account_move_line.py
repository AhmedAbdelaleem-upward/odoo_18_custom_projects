
from odoo import models, fields, _, api
import logging
logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    thirdparty_sku_id = fields.Char(string='Third-Party SKU ID', copy=False, readonly=False, help="Product SKU identifier from the third-party system")
