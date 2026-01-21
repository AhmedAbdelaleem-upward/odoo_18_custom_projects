from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class OneDriveAttendance(models.Model):
    _name = 'onedrive.attendance'
    _description = 'OneDrive Attendance Log'
    _order = 'check_time desc'

    user_id = fields.Integer(string='User ID', required=True, index=True, aggregator=False)
    check_time = fields.Datetime(string='Check Time', required=True, index=True)
    check_type = fields.Char(string='Check Type')  # I/O or similar
    sensor_id = fields.Char(string='Sensor ID')
    work_code = fields.Char(string='Work Code')
    sn = fields.Char(string='Serial Number')
    verify_code = fields.Char(string='Verify Code')
    user_ext_fmt = fields.Char(string='User Ext Fmt')
    memo_info = fields.Char(string='Memo Info')

    mdb_file_id = fields.Many2one('mdb.table.data', string='Source File', ondelete='cascade')

    # Sync tracking fields
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='HR Attendance',
        help='Reference to the created hr.attendance record',
        ondelete='set null',
    )
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('no_employee', 'No Employee Mapped'),
        ('error', 'Error'),
    ], string='Sync Status', default='pending', index=True)
    sync_error = fields.Text(string='Sync Error')

    _sql_constraints = [
        ('unique_attendance', 'unique(user_id, check_time, check_type, sensor_id)',
         'Attendance record must be unique (User + Time + Type + Sensor)!')
    ]

    def _is_check_in(self):
        """Check if this log represents a check-in event (case-insensitive)."""
        self.ensure_one()
        return self.check_type and self.check_type.upper() == 'I'

    def _is_check_out(self):
        """Check if this log represents a check-out event (case-insensitive)."""
        self.ensure_one()
        return self.check_type and self.check_type.upper() == 'O'

    @api.model
    def action_sync_to_hr_attendance(self, specific_logs=None):
        """
        Sync fingerprint attendance logs to hr.attendance records.
        Logic: Hybrid "First-In, Last-Out" with "Auto-Close Missing Out".
        - Same Day I -> I: Ignore (Keep First In).
        - Different Day I -> I: Close previous (End of day), Create New.
        - O -> O: Update previous (Keep Last Out).
        """
        _logger.info("Starting fingerprint to HR attendance sync...")

        if specific_logs:
            pending_logs = specific_logs.sorted(key=lambda r: (r.user_id, r.check_time))
            _logger.info(f"Processing specific batch of {len(pending_logs)} logs.")
        else:
            # Limit batch size to prevent timeout
            BATCH_SIZE = 2000
            
            # Get all pending logs, ordered by user and time
            # Also include 'error' status logs to retry them automatically
            pending_logs = self.search([
                ('sync_status', 'in', ['pending', 'error']),
                ('sync_error', 'not like', '%No employee mapped%'),
            ], order='user_id, check_time', limit=BATCH_SIZE)
            
            if not pending_logs:
                _logger.info("No pending fingerprint logs to sync.")
                return

        _logger.info("Processing batch of %d logs...", len(pending_logs))
        # Get employee mapping
        Employee = self.env['hr.employee']
        employees_with_fingerprint = Employee.search([
            ('fingerprint_user_id', '!=', False),
            ('fingerprint_user_id', '!=', 0),
        ])
        employee_map = {emp.fingerprint_user_id: emp for emp in employees_with_fingerprint}

        HrAttendance = self.env['hr.attendance']
        synced_count = 0
        error_count = 0

        # Group by user since we need sequential processing
        logs_by_user = {}
        for log in pending_logs:
            if log.user_id not in logs_by_user:
                logs_by_user[log.user_id] = []
            logs_by_user[log.user_id].append(log)

        # Local cache to track attendance records
        # Format: {employee_id: hr.attendance record (last one, open or closed)}
        local_open_attendance = {}
        
        # Pre-populate cache with LAST attendance record for each employee
        # This is critical to detect existing open records before processing
        employee_ids = [employee_map[uid].id for uid in logs_by_user.keys() if uid in employee_map]
        if employee_ids:
            for emp_id in employee_ids:
                last_att = HrAttendance.search([
                    ('employee_id', '=', emp_id),
                ], order='check_in desc', limit=1)
                if last_att:
                    local_open_attendance[emp_id] = last_att

        for fingerprint_user_id, logs in logs_by_user.items():
            employee = employee_map.get(fingerprint_user_id)

            if not employee:
                for log in logs:
                    log.write({
                        'sync_status': 'no_employee',
                        'sync_error': f'No employee found with fingerprint_user_id={fingerprint_user_id}',
                    })
                continue

            # Process logs for this employee
            for log in logs:
                try:
                    # Find the absolute last attendance record for this employee
                    last_attendance = local_open_attendance.get(employee.id)
                    
                    if not last_attendance:
                        HrAttendance.flush_model()
                        last_attendance = HrAttendance.search([
                            ('employee_id', '=', employee.id),
                        ], order='check_in desc', limit=1)

                    # CRITICAL: Check if this log is OLDER than the most recent record
                    # Odoo prevents inserting records before existing ones
                    if last_attendance:
                        last_check_time = last_attendance.check_out or last_attendance.check_in
                        if log.check_time < last_check_time:
                            log.write({
                                'sync_status': 'error',
                                'sync_error': f'Log date {log.check_time} is before existing attendance ending {last_check_time}. Historical records cannot be inserted.',
                            })
                            error_count += 1
                            continue

                    # Determine if Same Day
                    is_same_day = False
                    if last_attendance:
                        check_in_date = last_attendance.check_in.date()
                        new_date = log.check_time.date()
                        if check_in_date == new_date:
                            is_same_day = True

                    # --- LOGIC MATRIC ---
                    # 1. Same Day: Always update Check-Out (First In, Last Activity)
                    # 2. Different Day + Check-In: Close Previous, Create New.
                    # 3. Different Day + Check-Out: Error (Orphan).
                    
                    if is_same_day:
                        # Update existing record (extends shift)
                        last_attendance.write({
                            'check_out': log.check_time,
                        })
                        # Update local cache just in case (obj ref should be same)
                        local_open_attendance[employee.id] = last_attendance
                        
                        action_type = "Check-In" if log._is_check_in() else "Check-Out"
                        log.write({
                            'hr_attendance_id': last_attendance.id,
                            'sync_status': 'synced',
                            'sync_error': f'Updated Check-Out (Last {action_type} Logic)',
                        })
                        synced_count += 1
                        _logger.info(f"Updated check-out for {employee.name} to {log.check_time} ({action_type})")
                        continue

                    # Not Same Day (New Day or First Record)
                    # ANY log (In or Out) can start a new attendance record
                    # We set check_in = check_out = log time (closed record)
                    # Subsequent logs on same day will extend check_out
                    
                    # Close previous if still open
                    if last_attendance and not last_attendance.check_out:
                         check_in_date = last_attendance.check_in.date()
                         from datetime import time, datetime
                         close_time = datetime.combine(check_in_date, time(23, 59, 59))
                         last_attendance.write({
                            'check_out': close_time,
                            'out_mode': 'kiosk', 
                         })
                         if employee.id in local_open_attendance:
                             del local_open_attendance[employee.id]
                         _logger.info(f"Auto-closed previous attendance {last_attendance.id}")

                    # Create NEW Record with both check_in and check_out set
                    # This ensures single logs become complete records
                    log_type = "Check-In" if log._is_check_in() else "Check-Out"
                    hr_att = HrAttendance.create({
                        'employee_id': employee.id,
                        'check_in': log.check_time,
                        'check_out': log.check_time,  # Same time - single log = complete record
                        'in_mode': 'kiosk',
                        'out_mode': 'kiosk',
                    })
                    local_open_attendance[employee.id] = hr_att
                    
                    log.write({
                        'hr_attendance_id': hr_att.id,
                        'sync_status': 'synced',
                        'sync_error': False,
                    })
                    synced_count += 1
                    _logger.info(f"Created new record {hr_att.id} from {log_type} for {employee.name} at {log.check_time}")

                except Exception as e:
                    import traceback
                    _logger.error(traceback.format_exc())
                    log.write({
                        'sync_status': 'error',
                        'sync_error': str(e),
                    })
                    error_count += 1

        _logger.info(f"Fingerprint sync completed: {synced_count} synced, {error_count} errors")
        return True

    def action_retry_sync(self):
        """Reset sync status to pending for manual retry."""
        self.write({
            'sync_status': 'pending',
            'sync_error': False,
        })
        return True
