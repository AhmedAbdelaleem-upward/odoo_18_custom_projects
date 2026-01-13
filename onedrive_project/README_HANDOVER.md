# OneDrive MDB Integration for Odoo 18

A comprehensive Odoo 18 module for synchronizing Microsoft OneDrive files and processing ZKTeco biometric attendance data from Access Database (.mdb) files.

---

## 📋 Table of Contents

1. [Features](#-features)
2. [Installation](#-installation)
3. [Configuration](#-configuration)
4. [User Guide](#-user-guide)
5. [Developer Guide](#-developer-guide)
6. [Troubleshooting](#-troubleshooting)

---

## ✨ Features

- **OneDrive Integration**: Browse and download files directly from your Microsoft OneDrive.
- **MDB File Processing**: Parse Microsoft Access (.mdb) files, including large files (1.7GB+).
- **Attendance Logs**: Automatically extract employee check-in/out data from ZKTeco `CHECKINOUT` tables.
- **Daily Sync**: Scheduled job to automatically import new attendance data every night.
- **Duplicate Prevention**: Database-level constraints ensure no duplicate attendance records.
- **Background Processing**: Long-running imports run asynchronously via Cron jobs.

---

## 🚀 Installation

### Prerequisites

- Odoo 18 (Enterprise or Community)
- Python 3.10+
- PostgreSQL 14+

### Python Dependencies

```bash
pip install access-parser requests
```

### Module Installation

1. Clone or copy the `onedrive_integration_odoo` folder to your Odoo addons path.
2. Update your `odoo.conf` to include the path:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/custom/onedrive_project
   ```
3. Restart Odoo and install the module from **Apps**.

---

## ⚙️ Configuration

### 1. OneDrive API Credentials

Navigate to **Settings > OneDrive > Configuration** and enter:

| Field | Description |
|-------|-------------|
| **Client ID** | Azure App Registration Client ID |
| **Client Secret** | Azure App Registration Secret |
| **Tenant ID** | Your Azure AD Tenant ID |
| **Folder Path** | OneDrive folder to sync (e.g., `ATT Data`) |

### 2. Memory Limits for Large Files

For processing files over 500MB, update your `odoo.conf`:

```ini
limit_memory_soft = 6442450944   # 6GB
limit_memory_hard = 8589934592   # 8GB
limit_time_cpu = 3600            # 1 hour
limit_time_real = 3600           # 1 hour
limit_time_real_cron = 0         # Unlimited for crons
```

### 3. Development Mode (Optional)

To use a local file instead of downloading from OneDrive during development:

```ini
onedrive_environment = development
```

Place your test `.mdb` file at `~/Desktop/att2000.mdb`.

---

## 👤 User Guide

### Accessing the Dashboard

1. Go to **OneDrive Dashboard** from the main menu.
2. Click **Import** to sync files from OneDrive.

### Importing MDB Files

1. On the dashboard, locate your `.mdb` file.
2. Click **Read MDB** button.
3. A notification confirms "Import Started".
4. The import runs in the background - check **MDB Data** menu for progress.

### Viewing Attendance Logs

1. Go to **Attendance Logs** from the menu.
2. Use filters to search by:
   - User ID
   - Date Range
   - Check Type (In/Out)

### Scheduled Daily Sync

The system automatically syncs all MDB files from OneDrive every 24 hours.

- To trigger manually: **Settings > Technical > Scheduled Actions > OneDrive: Daily Sync**

---

## 🛠️ Developer Guide

### Module Structure

```
onedrive_integration_odoo/
├── models/
│   ├── onedrive_dashboard.py    # OneDrive API integration
│   ├── mdb_data.py              # MDB file parsing & import
│   ├── onedrive_attendance.py   # Attendance log model
│   └── res_config_settings.py   # Configuration
├── views/
│   ├── onedrive_dashboard_views.xml
│   ├── mdb_data_views.xml
│   └── onedrive_attendance_views.xml
├── data/
│   └── ir_cron_data.xml         # Scheduled actions
├── static/src/
│   ├── js/onedrive.js           # Dashboard OWL component
│   └── xml/onedrive_dashboard.xml
└── security/
    └── ir.model.access.csv
```

### Key Models

| Model | Description |
|-------|-------------|
| `onedrive.dashboard` | Handles OAuth tokens and OneDrive API calls |
| `mdb.table.data` | Stores imported MDB table metadata |
| `mdb.table.row` | Stores individual rows from MDB tables |
| `onedrive.attendance` | Structured attendance log records |

### Import Flow

```
User clicks "Read MDB"
        ↓
onedrive_dashboard.action_read_mdb_file()
        ↓
Creates mdb.table.data (status='pending')
        ↓
Triggers cron: cron_process_mdb_import
        ↓
mdb_data.process_import_job()
        ↓
Downloads file → Parses tables → Creates attendance records
        ↓
Status: 'done' (or 'failed')
```

### Adding Support for New Tables

To extract data from a new MDB table (e.g., `EMPLOYEES`):

1. **Create a new model** in `models/`:
   ```python
   class OneDriveEmployee(models.Model):
       _name = 'onedrive.employee'
       employee_id = fields.Integer()
       name = fields.Char()
   ```

2. **Update `process_single_table`** in `mdb_data.py`:
   ```python
   if table_name == 'EMPLOYEES':
       # Parse and create records
       self.env['onedrive.employee'].create({...})
   ```

3. **Create views and menu items** in `views/`.

### Duplicate Prevention Logic

The `onedrive.attendance` model uses a SQL unique constraint:

```python
_sql_constraints = [
    ('unique_attendance', 
     'unique(user_id, check_time, check_type, sensor_id)', 
     'Attendance record must be unique!')
]
```

The import uses `INSERT ... ON CONFLICT DO NOTHING` for high-performance duplicate skipping.

---

## 🔧 Troubleshooting

### "Import stuck at Pending"

- Check if the Cron job is active: **Settings > Technical > Scheduled Actions**
- Review logs: `tail -f /var/log/odoo/odoo.log | grep "MDB"`

### "Memory Error during import"

- Increase memory limits in `odoo.conf` (see Configuration section).
- Ensure only one large import runs at a time.

### "OneDrive authentication failed"

- Regenerate Client Secret in Azure Portal.
- Clear old tokens: Delete all records in `onedrive.dashboard`.

### "Attendance Logs empty after import"

- Verify the MDB file contains a `CHECKINOUT` table.
- Check for import errors in the `mdb.table.data` record's error message field.

---

## 📄 License

AGPL-3.0 - See LICENSE file for details.

## 👥 Contributors

- Cybrosys Technologies Pvt. Ltd. (Original OneDrive Integration)
- Custom MDB/Attendance extensions

---

*Last Updated: January 2026*