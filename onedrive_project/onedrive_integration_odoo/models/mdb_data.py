# -*- coding: utf-8 -*-
import json
import logging
import os
import math
import requests
import tempfile

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Try importing access_parser (pure Python MDB reader)
try:
    from access_parser import AccessParser
    HAS_ACCESS_PARSER = True
except ImportError:
    HAS_ACCESS_PARSER = False
    _logger.warning("access_parser not installed. Install with: pip install access-parser")


class MdbTableRow(models.Model):
    """Model to store individual rows of an MDB table"""
    _name = 'mdb.table.row'
    _description = 'MDB Table Row'
    
    table_id = fields.Many2one('mdb.table.data', string='Table', required=True, ondelete='cascade')
    data = fields.Text(string='Row Data (JSON)', help="JSON representation of the row values")


class MdbTableData(models.Model):
    """Model to store MDB file metadata and table structure"""
    _name = 'mdb.table.data'
    _description = 'MDB Table Metadata'
    _order = 'id desc'

    name = fields.Char(string='File Name', required=True)
    table_name = fields.Char(string='Table Name')
    columns = fields.Text(string='Columns (JSON)')
    # data field is deprecated but kept for backward compatibility if needed, though we won't populate it for large files
    data = fields.Text(string='Data (JSON)', help="Deprecated: Use row_ids for data access")
    
    row_ids = fields.One2many('mdb.table.row', 'table_id', string='Rows')
    row_count = fields.Integer(string='Row Count', compute='_compute_row_count', store=True)
    read_date = fields.Datetime(string='Read Date', default=fields.Datetime.now)

    # Async Import Fields
    status = fields.Selection([
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='pending')
    
    onedrive_file_id = fields.Char(string='OneDrive File ID')
    download_url = fields.Char(string='Download URL') 
    error_message = fields.Text(string='Error Message')

    @api.depends('row_ids')
    def _compute_row_count(self):
        for record in self:
            record.row_count = len(record.row_ids)

    def get_columns_list(self):
        """Return columns as a list"""
        if self.columns:
            return json.loads(self.columns)
        return []

    # Deprecated method kept for compatibility
    def get_data_list(self):
        """Return data as a list of lists (from deprecated data field)"""
        if self.data:
            return json.loads(self.data)
        return []

    def action_retry_import(self):
        """Button action to retry failed import"""
        for record in self:
            record.write({
                'status': 'pending',
                'error_message': False,
            })
            # Trigger cron immediately
            self.env.ref('onedrive_integration_odoo.cron_process_mdb_import').trigger()

    @api.model
    def process_import_job(self):
        """Cron job to process pending imports"""
        # Process one by one to avoid memory spikes
        pending_record = self.search([('status', '=', 'pending')], limit=1)
        if pending_record:
            _logger.info("Starting background import for %s", pending_record.name)
            try:
                pending_record.write({'status': 'downloading'})
                self.env.cr.commit() # Commit status change so UI updates
                
                # Download file
                file_path = pending_record._download_from_onedrive()
                
                # Backup to Desktop before processing (User Request)
                try:
                    desktop_path = os.path.expanduser("~/Desktop")
                    if os.path.exists(desktop_path):
                        backup_path = os.path.join(desktop_path, os.path.basename(file_path))
                        import shutil
                        shutil.copy2(file_path, backup_path)
                        _logger.info("Backup created at %s", backup_path)
                    else:
                        _logger.warning("Desktop folder not found at %s", desktop_path)
                except Exception as bkp_e:
                    _logger.warning("Failed to create backup: %s", str(bkp_e))

                pending_record.write({'status': 'processing'})
                self.env.cr.commit()

                # Process file
                pending_record.read_mdb_file(file_path, pending_record.name)
                
                pending_record.write({'status': 'done'})
                _logger.info("Background import completed for %s", pending_record.name)
                
                # Cleanup tmp file only (Desktop backup remains)
                if os.path.exists(file_path):
                    os.remove(file_path)

            except Exception as e:
                _logger.exception("MDB Import Failed for %s", pending_record.name)
                import traceback
                pending_record.write({
                    'status': 'failed',
                    'error_message': f"{str(e)}\n\n{traceback.format_exc()}"
                })
                self.env.cr.commit()

    def _download_from_onedrive(self):
        """Download file using stored URL or copy from Desktop in Dev mode"""
        self.ensure_one()
        
        # Environment Check
        env_mode = config.get('onedrive_environment')
        if env_mode == 'development':
            _logger.info("Environment is DEVELOPMENT. Looking for local file...")
            
            # Check multiple possible locations/names
            possible_paths = [
                os.path.expanduser("/home/ahmed/Desktop/odoo_mdb_92_att2000.mdb"),
                os.path.expanduser("~/Desktop/odoo_mdb_92_att2000.mdb"),
                os.path.expanduser("~/Desktop/att2000.mdb")
            ]
            
            desktop_path = None
            for p in possible_paths:
                if os.path.exists(p):
                    desktop_path = p
                    break
            
            if desktop_path:
                 temp_dir = tempfile.gettempdir()
                 clean_name = "".join([c for c in self.name if c.isalpha() or c.isdigit() or c in (' ', '.', '_')]).rstrip()
                 file_path = os.path.join(temp_dir, f"odoo_mdb_{self.id}_{clean_name}")
                 
                 import shutil
                 shutil.copy2(desktop_path, file_path)
                 _logger.info("Copied local file from %s to %s", desktop_path, file_path)
                 return file_path
            else:
                _logger.warning("Development mode enabled but no file found at %s. Falling back to download.", possible_paths)
                # Fallthrough to download logic if not found

        url = self.download_url
        if not url:
             raise UserError("No download URL provided")

        try:
            _logger.info("Downloading file from %s...", url)
            response = requests.get(url, stream=True, timeout=600) # 10 min timeout for download
            response.raise_for_status()
            
            temp_dir = tempfile.gettempdir()
            # Sanitize filename
            clean_name = "".join([c for c in self.name if c.isalpha() or c.isdigit() or c in (' ', '.', '_')]).rstrip()
            file_path = os.path.join(temp_dir, f"odoo_mdb_{self.id}_{clean_name}")
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024): # 1MB chunks
                    if chunk:
                        f.write(chunk)
            
            _logger.info("File downloaded to %s", file_path)
            return file_path
            
        except Exception as e:
            raise UserError(f"Failed to download file from OneDrive: {str(e)}")

    def read_mdb_file(self, file_path, file_name):
        """
        Read MDB file using access_parser (pure Python) and store data.
        """
        if not os.path.exists(file_path):
            raise UserError(f"File not found: {file_path}")

        if not HAS_ACCESS_PARSER:
            raise UserError(
                "access_parser library is not installed.\n"
                "Please install it with: pip install access-parser"
            )

        # Note: We are already inside a record method (self is a record or records)
        # But this method creates NEW records (tables) for the file.
        # The 'self' record here is likely the main file record placeholder if called from process_import_job
        
        # logic: read file -> find tables -> create mdb.table.data record for each table -> return them
        
        # WAIT: In the dashboard flow, we create ONE record per table.
        # But here we have a "pending record" which represents the FILE import request.
        # We should probably repurpose `mdb.table.data` to be `mdb.file` and have `mdb.table` as children?
        # OR, we just create multiple `mdb.table.data` records (one per table) like before.
        # AND update the 'pending_record' status? 
        # Actually, if `mdb.table.data` represents a TABLE, then the pending record is just a placeholder.
        # Ideally we should have:
        # 1. mdb.import.request (handles the file, status, download)
        # 2. mdb.table.data (the result tables)
        
        # However, to avoid HUGE refactoring, let's treat the 'pending_record' as the "Main" record 
        # (maybe we rename it to the first table found, or delete it and create new ones?)
        # A simpler approach for now:
        # The 'pending_record' tracks the import. We will use it to store the status.
        # When we find tables, we create NEW records for them.
        # The pending record can remain as a "Summary" or "Log" or we convert it to the first table.
        
        # Let's create new records for tables found, and mark the original "request" record as done (or delete it)?
        # Better: keep the request record as a "File" record if possible. 
        # But `mdb.table.data` has `table_name` field.
        
        # Hack for now: 
        # The pending record has `table_name` = False (or "Importing...").
        # We will keep it as a master record for status? 
        # Or better: `mdb.table.data` IS a table.
        # If the MDB has 10 tables, we get 10 records.
        # We only need ONE cron job to process the FILE.
        
        # Let's say we create a record with `table_name="Pending Import"`.
        # After processing, if we find 10 tables, we create 10 records.
        # What about the unexpected "Pending Import" record? We can delete it or convert it to be the first table.
        
        try:
            db = AccessParser(file_path)
            tables_catalog = db.catalog
        except Exception as e:
            _logger.error("Error opening MDB file: %s", str(e))
            raise UserError(f"Error opening MDB file: {str(e)}")

        if not tables_catalog:
            raise UserError(f"No tables found in the MDB file: {file_name}")

        # Ignore system tables
        table_names = [t for t in tables_catalog.keys() if not t.startswith('MSys')]
        
        if not table_names:
             _logger.warning("No user tables found in MDB file: %s", file_name)
             return

        first_table_name = table_names[0]
        other_table_names = table_names[1:]
        
        # Update SELF to be the first table
        self.process_single_table(db, first_table_name, is_self=True)
        
        # Create new records for other tables
        for table_name in other_table_names:
            new_record = self.sudo().create({
                'name': file_name,
                'status': 'processing',
                'download_url': self.download_url,
                'onedrive_file_id': self.onedrive_file_id,
            })
            new_record.process_single_table(db, table_name)
            new_record.write({'status': 'done'})

            
    def process_single_table(self, db, table_name, is_self=False):
        """Extract one table and save to current record"""
        try:
            _logger.info("Processing table: %s", table_name)
            
            # Get table object to ensure it exists
            acc_table = db.get_table(table_name)
            if not acc_table:
                _logger.warning("Table %s not found in Access catalog", table_name)
                return

            # Table parse() returns a dict where keys are column names
            table_data = acc_table.parse()
            columns = list(table_data.keys())
            
            if not columns: 
                _logger.info("Table %s has no data or columns", table_name)
                return

            # If existing record (is_self), update it. Else we should have created one.
            self.write({
                'table_name': table_name,
                'columns': json.dumps(columns),
            })
            
            # Flush immediately to ensure table_name is saved even if rows fail
            self.env.cr.commit()
            
            # Clear existing rows if any
            self.row_ids.unlink()

            # Special Cleanup for Attendance
            if table_name == 'CHECKINOUT':
                self.env['onedrive.attendance'].search([('mdb_file_id', '=', self.id)]).unlink()

            rows_to_create = []
            BATCH_SIZE = 1000
            total_rows_created = 0

            # Access table data via columns
            first_col = columns[0]
            # table_data[first_col] is a list of row values for that column
            row_data_list = table_data[first_col]
            num_rows = len(row_data_list) if isinstance(row_data_list, list) else 0

            
            attendance_batch = []

            for i in range(num_rows):
                row_vals = []
                # Helper to safely get value by col name
                def get_val(c):
                    col_data = table_data.get(c, [])
                    v = col_data[i] if i < len(col_data) else None
                    if v is None: return False 
                    return v

                for col in columns:
                    val = get_val(col)
                    if val is False: val = '' # Distinction: None/False from helper
                    elif isinstance(val, bytes): val = val.decode('utf-8', errors='replace')
                    else: val = str(val)
                    row_vals.append(val)
                
                # SPECIAL HANDLING FOR CHECKINOUT
                if table_name == 'CHECKINOUT':
                    try:
                        # Extract specific fields for Attendance Model
                        # Columns: ['USERID', 'CHECKTIME', 'VERIFYCODE', 'UserExtFmt', 'CHECKTYPE', 'SENSORID', 'Memoinfo', 'WorkCode', 'sn']
                        
                        # Helper to get raw value without str conversion for mapping
                        def get_raw(c):
                             val = get_val(c)
                             if val is False: return False
                             return val

                        att_vals = {
                            'user_id': int(get_raw('USERID')) if get_raw('USERID') else 0,
                            'check_time': get_raw('CHECKTIME'), # AccessParser usually returns datetime objects
                            'check_type': str(get_raw('CHECKTYPE')),
                            'sensor_id': str(get_raw('SENSORID')),
                            'work_code': str(get_raw('WorkCode')),
                            'sn': str(get_raw('sn')),
                            'mdb_file_id': self.id,
                        }
                        attendance_batch.append(att_vals)
                    except Exception as e:
                        _logger.warning("Failed to parse attendance row %d: %s", i, str(e))

                rows_to_create.append({
                    'table_id': self.id,
                    'data': json.dumps(row_vals)
                })

                if len(rows_to_create) >= BATCH_SIZE:
                    self.env['mdb.table.row'].create(rows_to_create)
                    total_rows_created += len(rows_to_create)
                    rows_to_create = []
                
                if len(attendance_batch) >= BATCH_SIZE:
                    self.env['onedrive.attendance'].create(attendance_batch)
                    attendance_batch = []
            
            # Flush existing generic rows
            if len(rows_to_create) > 0:
                 self.env['mdb.table.row'].create(rows_to_create)
                 total_rows_created += len(rows_to_create)

            # Flush remaining attendance records
            if len(attendance_batch) > 0:
                self.env['onedrive.attendance'].create(attendance_batch)
                    # Commit strictly not needed here if running in Cron (will confirm at end of trans), 
                    # but helps keep memory low in theory? access_parser is memory resident anyway.
            
            if rows_to_create:
                self.env['mdb.table.row'].create(rows_to_create)
                total_rows_created += len(rows_to_create)

            _logger.info("Finished table %s. Created %d rows.", table_name, total_rows_created)

        except Exception as e:
            _logger.error("Error processing table %s: %s", table_name, str(e))
            raise e
