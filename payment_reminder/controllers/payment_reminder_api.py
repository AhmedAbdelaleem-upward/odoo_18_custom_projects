import logging
from datetime import date

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentReminderAPI(http.Controller):
    def _check_api_key(self, request):
        """Check if the request contains the correct API key.

        Returns True if the check passes or if no API key is configured on the master.
        """
        env = request.env
        expected_key = (
            env["ir.config_parameter"]
            .sudo()
            .get_param("payment_reminder.api_key", "")
        )
        if not expected_key:
            # If no key is configured on master, allow all (backward compatibility/open mode)
            # OR you could decide to block all. For now, we allow if not configured.
            return True

        # Check header
        client_key = request.httprequest.headers.get("X-Odoo-Payment-Reminder-Secret")
        return client_key == expected_key

    @http.route(
        "/payment_reminder/register",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def register_client(self, **payload):
        """Public endpoint called from client instances to register/update themselves on Upward."""
        if not self._check_api_key(request):
            return {"status": "forbidden", "reason": "invalid_key"}

        env = request.env
        if (
            env["ir.config_parameter"]
            .sudo()
            .get_param("payment_reminder.role", "client_instance")
            != "upward_master"
        ):
            return {"status": "ignored", "reason": "not_upward_master"}

        vals = {
            "database_uuid": payload.get("database_uuid"),
            "base_url": payload.get("base_url"),
            "name": payload.get("name"),
        }
        client = (
            env["payment.reminder.client"]
            .sudo()
            .upsert_from_registration({k: v for k, v in vals.items() if v})
        )
        return {"status": "ok", "id": client.id if client else False}

    @http.route(
        "/payment_reminder/config/<string:database_uuid>",
        type="json",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def get_client_config(self, database_uuid, **kwargs):
        """Return current notification configuration for a client identified by database_uuid."""
        if not self._check_api_key(request):
            return {"active": False, "reason": "invalid_key"}

        env = request.env
        if (
            env["ir.config_parameter"]
            .sudo()
            .get_param("payment_reminder.role", "client_instance")
            != "upward_master"
        ):
            return {"active": False}

        client = (
            env["payment.reminder.client"]
            .sudo()
            .search([("database_uuid", "=", database_uuid)], limit=1)
        )
        if not client or not client.active_notification:
            return {"active": False}

        today = date.today()
        start = client.notification_start_date
        end = client.notification_end_date

        # Check if notification is active based on date range
        active = False
        if start and today >= start and (not end or today <= end):
            active = True

        # Days remaining until end date (payment deadline), for color logic
        days_remaining = None
        if end:
            days_remaining = (end - today).days

        # Determine color based on days remaining to deadline
        color = "green"
        if days_remaining is not None:
            if client.red_threshold_days is not None and days_remaining <= client.red_threshold_days:
                color = "red"
            elif (
                client.yellow_threshold_days is not None
                and days_remaining <= client.yellow_threshold_days
            ):
                color = "yellow"
            elif (
                client.green_threshold_days is not None
                and days_remaining <= client.green_threshold_days
            ):
                color = "green"

        # Select the correct message based on the determined color
        selected_message = ""
        template = None
        
        if color == "green":
            template = client.template_green_id
        elif color == "yellow":
            template = client.template_yellow_id
        elif color == "red":
            template = client.template_red_id

        if template and template.body:
            # Inject dynamic placeholders
            # We use safe format or just replace to avoid errors if placeholder is missing
            try:
                # Calculate absolute days for display (e.g. "15 days left")
                display_days = days_remaining if days_remaining is not None else 0
                selected_message = template.body.replace("{days}", str(display_days))
            except Exception:
                selected_message = template.body

        res = {
            "active": bool(active),
            "message": selected_message or "",
            "color": color,
            "days_remaining": days_remaining,
            "start_date": str(start) if start else None,
            "end_date": str(end) if end else None,
        }
        return res

