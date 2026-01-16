import json
import logging

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentReminderClientBanner(http.Controller):
    @http.route(
        "/payment_reminder/client/banner_config",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def banner_config(self):
        """Return banner configuration for the current database (client side).

        This controller is called from JS in any database (Upward or client).
        When running as client_instance, it will call the Upward master API
        using the database UUID.
        """
        env = request.env
        params = env["ir.config_parameter"].sudo()
        role = params.get_param("payment_reminder.role", "client_instance")

        # If this database is the master itself, never show the banner.
        if role == "upward_master":
            return {"active": False}

        master_url = params.get_param("payment_reminder.master_url")
        database_uuid = params.get_param("database.uuid")
        base_url = params.get_param("web.base.url")

        if not master_url or not database_uuid:
            return {"active": False}
        


        try:
            # Normalize master base URL (no trailing slash)
            master_url = master_url.rstrip("/")
            register_url = f"{master_url}/payment_reminder/register"
            config_url = f"{master_url}/payment_reminder/config/{database_uuid}"

            headers = {
                "Content-Type": "application/json",

            }

            # Register/refresh this client on the master (JSON-RPC format)
            register_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "database_uuid": database_uuid,
                    "base_url": base_url,
                    "name": request.env.cr.dbname,
                },
                "id": None,
            }
            requests.post(register_url, json=register_payload, headers=headers, timeout=5)

            # Fetch configuration (JSON-RPC format)
            config_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {},
                "id": None,
            }
            response = requests.post(config_url, json=config_payload, headers=headers, timeout=5)
            if response.ok:
                json_response = response.json()
                # Extract result from JSON-RPC wrapper
                data = json_response.get("result", {}) if isinstance(json_response, dict) else {}
                # Ensure the JSON has at least the keys we expect.
                data.setdefault("active", False)
                data.setdefault("message", "")
                data.setdefault("color", "green")
                return data
        except Exception as e:
            _logger.exception("Error while contacting Upward master for payment reminder: %s", e)

        return {"active": False}
