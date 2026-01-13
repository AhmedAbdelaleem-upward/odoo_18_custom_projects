# Odoo MDB OneDrive Integration - Technical Handover README

This document summarizes the optimizations and architectural changes implemented to support the processing of extremely large MDB files (1.7GB+) within Odoo 18.

## 1. Architectural Changes

### Data Modeling
- **Relational Storage**: Moved away from storing MDB data as a single JSON blob. Created a new model `mdb.table.row` to store individual rows, linked to a master `mdb.table.data` record.
- **Multi-Table Support**: The system now detects all tables within a single MDB file and creates a distinct `mdb.table.data` record for each (e.g., `CHECKINOUT`, `USERINFO`).

### Asynchronous Processing (Cron)
- **Background Jobs**: To bypass Odoo's HTTP worker timeout (120s), the download and parsing logic was moved to a scheduled action (`cron_process_mdb_import`).
- **Status Lifecycle**: Added a state machine to track progress: `pending` -> `downloading` -> `processing` -> `done` (or `failed`).
- **Concurrency**: The cron job processes one file at a time to manage system resources.

## 2. Large File Optimizations

### Memory Management
- **Batching**: Implemented 1,000-row batching for database writes in `process_single_table`.
- **System Limits**: Updated `onedrive.conf` to accommodate `access_parser` (which loads the entire file binary into memory and slices it):
  - `limit_memory_soft`: 6GB
  - `limit_memory_hard`: 8GB
  - `limit_time_real_cron`: 0 (Unlimited for Crons)

### Download Logic
- **Streaming**: Used `requests.get(stream=True)` to download 1.7GB files efficiently to `/tmp` without saturating the Odoo worker memory.
- **Cleanup**: Implemented automatic deletion of temporary `.mdb` files from `/tmp` after processing is complete.

## 3. Bug Fixes & Refinements

### Backend (Python)
- **Catalog Integration**: Fixed a `KeyError: 0` by correctly iterating over the `db.catalog` dictionary in `access_parser`.
- **System Table Filtering**: Automatically ignores tables starting with `MSys*` to reduce noise and overhead.
- **Cron Method**: Updated the manual trigger call to `._trigger()` as per Odoo 18 requirements.

### Frontend (JS/XML)
- **Context Binding**: Fixed a `TypeError` in the dashboard by adding `this.` prefix to OWL component method calls.
- **Progress Feedback**: Updated the dashboard to provide immediate visual feedback ("Import Started") while the background job queues.
- **UI States**: Added a status bar and error alert box to the `mdb.table.data` form view for better user transparency.

## 4. Current Configuration (onedrive.conf)
Crucial settings for the next agent:
```ini
addons_path = .../odoo/addons, .../custom/onedrive_project
xmlrpc_port = 8061
limit_memory_soft = 6442450944
limit_memory_hard = 8589934592
limit_time_cpu = 3600
limit_time_real = 3600
limit_time_real_cron = 0
```

## 5. Known Context
- **OneDrive Path**: Files are synchronized from the `ATT Data` folder.
- **File Type**: Primarily ZKTeco biometric database files containing attendance logs (`CHECKINOUT`).
