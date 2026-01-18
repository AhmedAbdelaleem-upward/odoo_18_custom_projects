# Payment Reminder Usage Guide

## Installation
1. Copy the `payment_reminder` module to your Odoo `custom` addons directory.
2. Update your Odoo configuration (or use the web interface) to include the new path.
3. Install the module from the Odoo Apps dashboard.

## Setup
### 1. Identify Database Role
Determine if this database will be the **Upward Master** (central control) or a **Client Instance**.

### 2. Configure Master Instance
- Go to **Settings > General Settings > Payment Reminder**.
- Set **Payment Reminder Role** to `Upward Master`.
- Save.
- Use the **Payment Reminder** app menu to manage client configurations.

### 3. Configure Client Instance
- Go to **Settings > General Settings > Payment Reminder**.
- Set **Payment Reminder Role** to `Client Instance`.
- Enter the **Upward Master Base URL** (e.g., `http://master.example.com`).
- Save.

## How it Works
- The master instance stores settings for each client (identified by their UUID).
- Clients periodically fetch their configuration via RPC.
- If an alert is active, a colored banner (Green/Yellow/Red) appears at the top of the client's Odoo interface to remind them of pending payments.
