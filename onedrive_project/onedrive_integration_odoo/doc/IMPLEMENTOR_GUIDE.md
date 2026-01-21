# OneDrive Integration - Implementor Guide

This guide is for Odoo implementors setting up the OneDrive Fingerprint Attendance Integration module.

---

## Table of Contents
1. [Module Overview](#module-overview)
2. [Setup Steps](#setup-steps)
3. [Cron Jobs & Timing](#cron-jobs--timing)
4. [Attendance Sync Logic](#attendance-sync-logic)
5. [System Parameters](#system-parameters)
6. [Troubleshooting](#troubleshooting)

---

## Module Overview

This module connects:
- **OneDrive** (Microsoft cloud storage) → Contains `.mdb` fingerprint attendance files
- **Odoo HR Attendance** → Creates employee check-in/check-out records

### Data Flow
```
OneDrive (.mdb files)
       ↓ [Daily Sync Cron]
mdb.table.data (queued files)
       ↓ [Process MDB Cron - Every 1 min]
onedrive.attendance (raw fingerprint logs)
       ↓ [HR Sync Cron - Daily at 1 AM]
hr.attendance (Odoo HR records)
```

---

## Setup Steps

### 1. Microsoft Azure Configuration
1. Create an Azure App Registration
2. Set **Redirect URI** to: `https://your-odoo-domain/onedrive/authentication`
3. Grant API permissions: `offline_access`, `Files.ReadWrite`
4. Copy **Client ID**, **Client Secret**, and **Tenant ID**

### 2. Odoo Configuration
Go to **Settings → General Settings → OneDrive Integration**:
- **Client ID**: From Azure
- **Client Secret**: From Azure
- **Tenant ID**: From Azure
- **Folder Path**: OneDrive folder containing MDB files (e.g., `ATT Data`)

### 3. Employee Mapping
Each employee needs a **Fingerprint User ID** to match device logs:
1. Go to **Employees → Select Employee → HR Settings tab**
2. Set **Fingerprint User ID** = Device User ID (from fingerprint device)

---

## Cron Jobs & Timing

| Cron Job                                        | Schedule                 | Purpose                                          |
| ----------------------------------------------- | ------------------------ | ------------------------------------------------ |
| **OneDrive: Daily Sync**                        | Every 1 Day              | Scans OneDrive folder, queues new `.mdb` files   |
| **OneDrive: Process MDB Imports**               | Every 1 Minute           | Downloads & parses queued MDB files              |
| **OneDrive: Sync Fingerprint to HR Attendance** | Daily at 1:00 AM (UTC-1) | Creates `hr.attendance` records from parsed logs |

### Recommended Sequence
1. **Daily Sync** runs first (e.g., at midnight)
2. **Process MDB** runs immediately after (every minute until done)
3. **HR Attendance Sync** runs last (at 1 AM when all data is ready)

---

## Attendance Sync Logic

### Check-In / Check-Out Rules

The system uses **"First-In, Last-Activity"** logic:

| Scenario                         | Action                                                    |
| -------------------------------- | --------------------------------------------------------- |
| First log of the day (In or Out) | Creates new record with `check_in = check_out = log_time` |
| Same day, additional log         | Updates `check_out` to the new log time                   |
| New day, previous record open    | Closes previous at 23:59:59, creates new record           |

### Example Scenarios

#### Scenario 1: Normal Day
```
09:00 Check-In  → Creates record: check_in=09:00, check_out=09:00
18:00 Check-Out → Updates record: check_in=09:00, check_out=18:00
Result: 1 record (9 hours worked)
```

#### Scenario 2: Multiple Badges ("Burst")
```
09:00 Check-In  → Creates: check_in=09:00, check_out=09:00
09:01 Check-In  → Updates: check_in=09:00, check_out=09:01
09:05 Check-In  → Updates: check_in=09:00, check_out=09:05
17:00 Check-Out → Updates: check_in=09:00, check_out=17:00
17:05 Check-Out → Updates: check_in=09:00, check_out=17:05
Result: 1 record (check_in=09:00, check_out=17:05)
```

#### Scenario 3: Forgot to Check Out
```
Day 1: 09:00 Check-In → Creates: check_in=09:00, check_out=09:00
Day 2: 09:00 Check-In → Closes Day 1 at 23:59:59, Creates new Day 2 record
Result: Day 1 record auto-closed, Day 2 starts fresh
```

#### Scenario 4: Single Log Day
```
12:00 Check-In (only log) → Creates: check_in=12:00, check_out=12:00
Result: 1 record with 0 hours (valid but indicates incomplete data)
```

---

## System Parameters

Configure these in **Settings → Technical → System Parameters**:

| Key                                                    | Default | Description                    |
| ------------------------------------------------------ | ------- | ------------------------------ |
| `onedrive_integration_odoo.attendance_sync_batch_size` | `2000`  | Records processed per cron run |

---

## Troubleshooting

### Sync Status Values
- **pending** - Waiting to be processed
- **synced** - Successfully created/updated HR attendance
- **no_employee** - No employee found with matching Fingerprint User ID
- **error** - Processing failed (check `sync_error` field)

### Common Issues

| Issue                                   | Solution                                                      |
| --------------------------------------- | ------------------------------------------------------------- |
| "No employee mapped"                    | Set `Fingerprint User ID` on employee form                    |
| "Historical records cannot be inserted" | Log date is before existing attendance; reset attendance data |
| Duplicate entries                       | Check SQL constraint on `onedrive.attendance`                 |
| Cron not running                        | Verify cron is active and check server logs                   |

### Manual Retry
1. Go to **OneDrive → Attendance Logs**
2. Filter by `Sync Status = Error`
3. Select records → **Action → Mark as To Sync**
4. Trigger sync cron or wait for next run

---

## Menu Navigation

- **OneDrive → Dashboard** - Main OneDrive file browser
- **OneDrive → MDB Data** - View imported table data
- **OneDrive → Attendance Logs** - Raw fingerprint logs with sync status
- **Settings → Scheduled Actions** - Configure cron timing
- **HR → Attendance** - Final synced attendance records
