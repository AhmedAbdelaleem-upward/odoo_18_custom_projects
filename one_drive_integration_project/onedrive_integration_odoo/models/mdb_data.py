# -*- coding: utf-8 -*-
import json
import logging
import os

from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Try importing access_parser (pure Python MDB reader)
try:
    from access_parser import AccessParser
    HAS_ACCESS_PARSER = True
except ImportError:
    HAS_ACCESS_PARSER = False
    _logger.warning("access_parser not installed. Install with: pip install access-parser")


class MdbTableData(models.Model):
    """Model to store MDB file data"""
    _name = 'mdb.table.data'
    _description = 'MDB Table Data'
    _order = 'id desc'

    name = fields.Char(string='File Name', required=True)
    table_name = fields.Char(string='Table Name', required=True)
    columns = fields.Text(string='Columns (JSON)')
    data = fields.Text(string='Data (JSON)')
    row_count = fields.Integer(string='Row Count', compute='_compute_row_count', store=True)
    read_date = fields.Datetime(string='Read Date', default=fields.Datetime.now)

    @api.depends('data')
    def _compute_row_count(self):
        for record in self:
            if record.data:
                try:
                    rows = json.loads(record.data)
                    record.row_count = len(rows)
                except Exception:
                    record.row_count = 0
            else:
                record.row_count = 0

    def get_columns_list(self):
        """Return columns as a list"""
        if self.columns:
            return json.loads(self.columns)
        return []

    def get_data_list(self):
        """Return data as a list of lists"""
        if self.data:
            return json.loads(self.data)
        return []

    @api.model
    def read_mdb_file(self, file_path, file_name):
        """
        Read MDB file using access_parser (pure Python) and store data in this model.
        Returns the created records.
        """
        if not os.path.exists(file_path):
            raise UserError(f"File not found: {file_path}")

        if not HAS_ACCESS_PARSER:
            raise UserError(
                "access_parser library is not installed.\n"
                "Please install it with: pip install access-parser\n"
                "Or add 'access-parser' to your requirements.txt"
            )

        try:
            # Parse the MDB file using access_parser
            db = AccessParser(file_path)
        except Exception as e:
            _logger.error("Error opening MDB file: %s", str(e))
            raise UserError(f"Error opening MDB file: {str(e)}")

        # Get list of tables from the catalog
        tables = db.catalog
        if not tables:
            raise UserError("No tables found in the MDB file.")

        _logger.info("Found %d tables in MDB file: %s", len(tables), list(tables))

        created_records = []

        # Delete old records for this file
        self.search([('name', '=', file_name)]).unlink()

        for table_name in tables:
            try:
                # Parse the table
                table = db.parse_table(table_name)

                if table is None:
                    _logger.warning("Table %s could not be parsed", table_name)
                    continue

                # Get column names
                columns = list(table.columns) if hasattr(table, 'columns') else []

                # Get data rows - table is a dict-like object with column names as keys
                rows = []
                if columns:
                    # Get the number of rows from the first column
                    first_col = columns[0]
                    num_rows = len(table[first_col]) if first_col in table else 0

                    for i in range(num_rows):
                        row = []
                        for col in columns:
                            value = table[col][i] if col in table and i < len(table[col]) else None
                            # Convert value to string for JSON serialization
                            if value is None:
                                row.append('')
                            elif isinstance(value, bytes):
                                row.append(value.decode('utf-8', errors='replace'))
                            else:
                                row.append(str(value))
                        rows.append(row)

                _logger.info("Table %s: %d columns, %d rows", table_name, len(columns), len(rows))

                # Create record
                record = self.create({
                    'name': file_name,
                    'table_name': table_name,
                    'columns': json.dumps(columns),
                    'data': json.dumps(rows),
                })
                created_records.append(record)

            except Exception as e:
                _logger.error("Error parsing table %s: %s", table_name, str(e))
                continue

        if not created_records:
            raise UserError("Could not read any tables from the MDB file.")

        return created_records
