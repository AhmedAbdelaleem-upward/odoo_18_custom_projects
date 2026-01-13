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
import requests
from odoo import exceptions, fields, models, _


class UploadFile(models.TransientModel):
    """
    For opening wizard view
    """
    _name = "upload.file"
    _description = "Upload File"

    file = fields.Binary(string="Attachment", help="Select a file to upload")
    file_name = fields.Char(string="File Name", help="Name of the attachment")

    def action_upload_file(self):
        """
        Upload file to onedrive
        """
        if not self.file:
            raise exceptions.UserError(_('Please Attach a file to upload.'))
        attachment = self.env["ir.attachment"].search(
            ['|', ('res_field', '!=', False), ('res_field', '=', False),
             ('res_id', '=', self.id),
             ('res_model', '=', 'upload.file')])
        token = self.env['onedrive.dashboard'].search([], order='id desc',
                                                      limit=1)
        if not token:
            raise exceptions.UserError(
                _('Please setup Access Token first.'))
        if token.token_expiry_date <= str(fields.Datetime.now()):
            token.generate_onedrive_refresh_token()

        folder_path = self.env['ir.config_parameter'].get_param(
            'onedrive_integration_odoo.folder_id', '').strip('/')

        try:
            # Build URL based on folder path
            if folder_path:
                url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}/{self.file_name}:/createUploadSession"
            else:
                url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{self.file_name}:/createUploadSession"

            upload_session = requests.post(url, headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token.onedrive_access_token
            })
            upload_session.raise_for_status()

            upload_url = upload_session.json().get('uploadUrl')
            if not upload_url:
                raise exceptions.UserError(_('Failed to create upload session.'))

            requests.put(upload_url, data=open(
                (attachment._full_path(attachment.store_fname)), 'rb'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': 'File has been uploaded successfully. '
                               'Please refresh.',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as error:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'Failed to upload: %s' % error,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
