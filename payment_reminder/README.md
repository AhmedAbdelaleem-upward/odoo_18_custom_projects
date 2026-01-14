Payment Reminder (Upward Master & Client)
=========================================

This module is designed to be reusable on any Odoo 18 database. The same
module is installed on:

- **Upward master instance**: manages client databases and their payment alerts.
- **Client instances**: display a coloured banner similar to the Odoo subscription
  expiration warning, based on configuration from the master.

Configuration
-------------

1. **Install the module** `payment_reminder` on both the master and all clients.

2. **On the Upward master database:**
   - Go to `Settings > General Settings > Payment Reminder`.
   - Set **Payment Reminder Role** = `Upward Master`.
   - Save.
   - Go to `Payment Reminder > Clients` to manage client notification settings
     (on/off, dates, colour thresholds, Arabic message, etc.).

3. **On each client database:**
   - Go to `Settings > General Settings > Payment Reminder`.
   - Set **Payment Reminder Role** = `Client Instance`.
   - Set **Upward Master Base URL** to the external URL of the master, e.g.
     `http://upward.example.com:8069`.
   - Save.

How it works
------------

- Each client database has a unique `database.uuid` (from `ir.config_parameter`).
- A scheduled action and a lightweight JS call will:
  - Register the client on the master using this `database.uuid`.
  - Ask the master for the current notification config.
- The master:
  - Stores one `payment.reminder.client` record per client database.
  - Lets Upward administrators control:
    - On/off switch.
    - Start/end dates.
    - Colour thresholds (green / yellow / red based on remaining days).
    - The message text (Arabic or any language).
- Client instances show a top fixed banner in the backend when the master says
  the alert is active.

Config file
-----------

An example config template is provided at `config/payment_reminder.conf`. It
documents the system parameters used by the module:

- `payment_reminder.role`
- `payment_reminder.master_url`

