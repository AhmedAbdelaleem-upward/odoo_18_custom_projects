from odoo import models, fields, api

class OneDriveAttendance(models.Model):
    _name = 'onedrive.attendance'
    _description = 'OneDrive Attendance Log'
    _order = 'check_time desc'

    user_id = fields.Integer(string='User ID', required=True, index=True, group_operator=False)
    check_time = fields.Datetime(string='Check Time', required=True, index=True)
    check_type = fields.Char(string='Check Type') # I/O or similar
    sensor_id = fields.Char(string='Sensor ID')
    work_code = fields.Char(string='Work Code')
    sn = fields.Char(string='Serial Number')
    verify_code = fields.Char(string='Verify Code')
    user_ext_fmt = fields.Char(string='User Ext Fmt')
    memo_info = fields.Char(string='Memo Info')
    
    mdb_file_id = fields.Many2one('mdb.table.data', string='Source File', ondelete='cascade')

    _sql_constraints = [
        ('unique_attendance', 'unique(user_id, check_time, check_type, sensor_id)', 
         'Attendance record must be unique (User + Time + Type + Sensor)!')
    ]
