# -*- coding: utf-8 -*-
###############################################################################
#
#   Cybrosys Technologies Pvt. Ltd.
#
#   Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#   Author: Jumana Haseen ( odoo@cybrosys.com )
#
#   You can modify it under the terms of the GNU AFFERO
#   GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#   You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#   (AGPL v3) along with this program.
#   If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import json
import logging
import requests
from datetime import timedelta
from odoo import fields, models
from odoo.exceptions import UserError
import tempfile
import os
_logger = logging.getLogger(__name__)


class OneDriveDashboard(models.Model):
    """
    Generate refresh and  access token
    """
    _name = 'onedrive.dashboard'
    _description = "Generate access and refresh tokens "

    onedrive_access_token = fields.Char(
        string="OneDrive Access Token",
        store=True,
        help="Access token for authenticating and accessing OneDrive APIs.")
    onedrive_refresh_token = fields.Char(
        string="OneDrive Refresh Token",
        help="Refresh token for obtaining a new access token when the current "
             "one expires.")
    token_expiry_date = fields.Char(
        string="OneDrive Token Validity",
        help="Validity period of the access token, indicating until when it is"
             " valid.")
    upload_file = fields.Binary(
        string="Upload File",
        help="Binary field to store the uploaded file.")

    def get_tokens(self, authorize_code):
        """
        Generate onedrive tokens from authorization code
        """
        data = {
            'code': authorize_code,
            'client_id': self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.client_id', ''),
            'client_secret': self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.client_secret', ''),
            'grant_type': 'authorization_code',
            # 'scope': ['offline_access Files.ReadWrite.All'],
            'scope': 'offline_access Files.ReadWrite',
            'redirect_uri': self.env['ir.config_parameter'].get_param(
                'web.base.url') + '/onedrive/authentication'
        }
        try:
            # res = requests.post(
            #     "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            #     data=data,
            #     headers={"content-type": "application/x-www-form-urlencoded"})
            TENANT_ID = self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.tenant_id'
            )
            res = requests.post(
                f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
                data=data,
                headers={"content-type": "application/x-www-form-urlencoded"})
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.env['onedrive.dashboard'].create({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'token_expiry_date': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in else False,
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !",
                              error.response.content)
            raise error

    def generate_onedrive_refresh_token(self):
        """
        Generate onedrive access token from refresh token if expired
        """
        data = {
            'client_id': self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.client_id', ''),
            'client_secret': self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.client_secret', ''),
            # 'scope': ['offline_access openid Files.ReadWrite.All'],
            'scope': 'offline_access Files.ReadWrite',
            'grant_type': "refresh_token",
            'redirect_uri': self.env['ir.config_parameter'].get_param(
                'web.base.url') + '/onedrive/authentication',
            'refresh_token': self.onedrive_refresh_token
        }
        try:
            TENANT_ID = self.env['ir.config_parameter'].get_param(
                'onedrive_integration_odoo.tenant_id'
            )
            res = requests.post(
                f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
                data=data,
                headers={"Content-type": "application/x-www-form-urlencoded"})
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'token_expiry_date': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in else False,
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !",
                              error.response.content)
            raise error

    def action_synchronize_onedrive(self):
        record = self.search([], order='id desc', limit=1)
        if not record:
            return False

        if record.token_expiry_date <= str(fields.Datetime.now()):
            record.generate_onedrive_refresh_token()

        folder_path = self.env['ir.config_parameter'].get_param(
            'onedrive_integration_odoo.folder_id', ''
        ).strip('/')

        if folder_path:
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"
        else:
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"

        _logger.info("OneDrive API URL: %s", url)
        response = requests.get(
            url,
            headers={'Authorization': 'Bearer ' + record.onedrive_access_token}
        )

        data = response.json()
        _logger.info("OneDrive API Response items count: %s", len(data.get('value', [])))
        for item in data.get('value', []):
            _logger.info("OneDrive item: name=%s, has_download_url=%s, is_folder=%s",
                        item.get('name'),
                        '@microsoft.graph.downloadUrl' in item,
                        'folder' in item)

        if 'error' in data:
            raise UserError(data['error']['message'])

        def _get_icon(name):
            name = name.lower()
            if name.endswith('.mdb'):
                return '/onedrive_integration_odoo/static/src/img/mdb1.png'
            if name.endswith('.pdf'):
                return '/onedrive_integration_odoo/static/src/img/pdf.png'
            if name.endswith(('.xlsx', '.xls')):
                return '/onedrive_integration_odoo/static/src/img/excel.png'
            if name.endswith(('.png', '.jpg', '.jpeg')):
                return '/onedrive_integration_odoo/static/src/img/image.png'
            return '/onedrive_integration_odoo/static/src/img/file.png'


        return [
            {
                "name": item['name'],
                "download_url": item['@microsoft.graph.downloadUrl'],
                "is_mdb": item['name'].lower().endswith('.mdb'),
                "id": item.get('id'), # Pass the ID
                "icon": _get_icon(item['name']),   # 👈 ADD THIS
                "ext": item['name'].split('.')[-1].lower(),  # 👈 ADD THIS
            }
            for item in data.get('value', [])
            if '@microsoft.graph.downloadUrl' in item
        ]



    def action_read_mdb_file(self, download_url, filename, onedrive_file_id=False):
        """
        Create a pending import record and trigger background processing.
        """
        # Create pending record
        _logger.info("Queuing MDB import for %s", filename)
        
        # Check if we already have a pending/processing import for this file
        existing = self.env['mdb.table.data'].search([
            ('name', '=', filename),
            ('status', 'in', ['pending', 'downloading', 'processing'])
        ], limit=1)
        
        if existing:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import in Progress',
                    'message': f"There is already an import running for {filename}.",
                    'type': 'warning',
                    'sticky': False,
                }
            }
            
        import_record = self.env['mdb.table.data'].create({
            'name': filename,
            'table_name': 'Pending Import...',
            'status': 'pending',
            'download_url': download_url,
            'onedrive_file_id': onedrive_file_id,
        })
        
        # Trigger cron to run immediately
        self.env.ref('onedrive_integration_odoo.cron_process_mdb_import')._trigger()
        
        # Notify user
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Started',
                'message': f"Import for {filename} started in background. Please check MDB Data menu shortly.",
                'type': 'success',
                'sticky': False,
            }
        }
    def action_daily_sync(self):
        """
        Daily Scheduled Action:
        1. Scan OneDrive for all .mdb files
        2. Queue them for import (if not already pending/processing)
        """
        _logger.info("Starting Daily OneDrive Sync...")
        try:
             # 1. Get all files
             files = self.action_synchronize_onedrive()
             if not files:
                 _logger.info("No files found on OneDrive.")
                 return
             
             # 2. Filter MDBs
             mdb_files = [f for f in files if f.get('is_mdb')]
             _logger.info("Found %d MDB files to sync.", len(mdb_files))
             
             count_queued = 0
             for f in mdb_files:
                 # 3. Queue Import (reuse existing logic)
                 # We check existing inside action_read_mdb_file but returns dict.
                 # Let's call internal logic directly to be cleaner.
                 
                 existing = self.env['mdb.table.data'].search([
                    ('name', '=', f['name']),
                    ('status', 'in', ['pending', 'downloading', 'processing'])
                 ], limit=1)
                 
                 if existing:
                     _logger.info("Skipping %s (already in progress)", f['name'])
                     continue
                     
                 # Create pending record
                 self.env['mdb.table.data'].create({
                    'name': f['name'],
                    'table_name': 'Pending Import...',
                    'status': 'pending',
                    'download_url': f['download_url'],
                    'onedrive_file_id': f['id'],
                 })
                 count_queued += 1
                 
             # Trigger processor
             if count_queued > 0:
                 self.env.ref('onedrive_integration_odoo.cron_process_mdb_import')._trigger()
                 _logger.info("Queued %d files for background processing.", count_queued)
                 
        except Exception as e:
            _logger.exception("Daily Sync Failed")
