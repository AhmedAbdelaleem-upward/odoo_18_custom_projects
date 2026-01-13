from odoo import models, fields, api

class OneDriveAttendance(models.Model):
    _name = 'onedrive.attendance'
    _description = 'OneDrive Attendance Log'
    _order = 'check_time desc'

    user_id = fields.Integer(string='User ID', required=True, index=True)
    check_time = fields.Datetime(string='Check Time', required=True, index=True)
    check_type = fields.Char(string='Check Type') # I/O or similar
    sensor_id = fields.Char(string='Sensor ID')
    work_code = fields.Char(string='Work Code')
    sn = fields.Char(string='Serial Number')
    
    mdb_file_id = fields.Many2one('mdb.table.data', string='Source File', ondelete='cascade')
