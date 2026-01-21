# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    """Extend hr.employee to add fingerprint user ID for attendance sync."""
    _inherit = 'hr.employee'

    fingerprint_user_id = fields.Integer(
        string='Fingerprint User ID',
        help='User ID from the fingerprint attendance device. Used to link '
             'fingerprint logs to this employee.',
        index=True,
    )
