# Bashraheel Invoice Integration API

This document describes how to use the FastAPI endpoints for invoice management.

## Base URL

```
http://localhost:8061/api/v1
```

## Authentication

All endpoints require JWT Bearer token authentication.

**Get a Token:**
```bash
curl -X 'POST' 'http://localhost:8061/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"login": "admin", "password": "admin"}'
```

Use the `access_token` from the response in the `Authorization` header.

---

## Endpoints

### 1. Create Invoice

**POST** `/invoice/create`

Creates one or more invoices and submits to ZATCA.

```bash
curl -X 'POST' 'http://localhost:8061/api/v1/invoice/create' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJwYXJ0bmVyX2lkIjozLCJlbWFpbCI6ImFkbWluIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc2ODczNjczMywiaWF0IjoxNzY4NzMzMTMzfQ.nQYSrei8__k2Ak0wdZl7DZ5NB5LraN7K-GUZxePlrLA' \
  -H 'Content-Type: application/json' \
  -d '{
    "invoiceList": [{
      "invoiceNo": "INV-001",
      "move_type": "out_invoice",
      "documentDate": "2025-02-15",
      "thirdparty_sa_confirmation_datetime": "2025-02-15 10:30:00",
      "store": {"id": "STORE001"},
      "lines": [
        {"skuCode": "PRODUCT-SKU", "qty": 2, "sellingPrice": 50.0, "discount": 0}
      ]
    }]
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `invoiceNo` | Yes | Unique invoice reference |
| `move_type` | Yes | `out_invoice` for sales |
| `documentDate` | Yes | Format: `YYYY-MM-DD` |
| `thirdparty_sa_confirmation_datetime` | Yes | Format: `YYYY-MM-DD HH:MM:SS` |
| `store.id` | Yes | Store identifier |
| `lines[].skuCode` | Yes | Product SKU (used as description) |
| `lines[].qty` | Yes | Quantity (> 0) |
| `lines[].sellingPrice` | Yes | Unit price |
| `lines[].discount` | No | Discount % (0-100) |

---

### 2. Create Refund

**POST** `/invoice/create`

Creates partial or full refunds for existing invoices.

#### Partial Refund
```bash
curl -X 'POST' 'http://localhost:8061/api/v1/invoice/create' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJwYXJ0bmVyX2lkIjozLCJlbWFpbCI6ImFkbWluIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc2ODczNjczMywiaWF0IjoxNzY4NzMzMTMzfQ.nQYSrei8__k2Ak0wdZl7DZ5NB5LraN7K-GUZxePlrLA' \
  -H 'Content-Type: application/json' \
  -d '{
    "invoiceList": [{
      "invoiceNo": "REF-020",
      "main_invoiceNo": "INV-020",
      "move_type": "out_refund",
      "out_refund_type": "partial",
      "documentDate": "2025-02-16",
      "thirdparty_sa_confirmation_datetime": "2025-02-16 10:30:00",
      "store": {"id": "STORE001"},
      "lines": [
        {"skuCode": "PRODUCT-SKU", "qty": 1, "sellingPrice": 5000.0, "discount": 0}
      ]
    }]
  }'
```

#### Full Refund
```bash
curl -X 'POST' 'http://localhost:8061/api/v1/invoice/create' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJwYXJ0bmVyX2lkIjozLCJlbWFpbCI6ImFkbWluIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc2ODczNjczMywiaWF0IjoxNzY4NzMzMTMzfQ.nQYSrei8__k2Ak0wdZl7DZ5NB5LraN7K-GUZxePlrLA' \
  -H 'Content-Type: application/json' \
  -d '{
    "invoiceList": [{
      "invoiceNo": "REF-021",
      "main_invoiceNo": "INV-020",
      "move_type": "out_refund",
      "out_refund_type": "full",
      "documentDate": "2025-02-16",
      "thirdparty_sa_confirmation_datetime": "2025-02-16 10:30:00",
      "store": {"id": "STORE001"},
      "lines": [{"skuCode": "DUMMY", "qty": 1, "sellingPrice": 0, "discount": 0}]
    }]
  }'
```

> **Note:** Full refunds ignore `lines` but require at least one dummy line for validation.

| Field | Required | Description |
|-------|----------|-------------|
| `main_invoiceNo` | Yes | Original invoice to refund |
| `out_refund_type` | Yes | `full` or `partial` |

---

### 3. Report Invoices

**POST** `/invoice/report`

Query invoices by store and date.

```bash
curl -X 'POST' 'http://localhost:8061/api/v1/invoice/report' \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"store_id": "STORE001", "date": "2025-02-15"}'
```

**Response includes:**
- `odoo_invoice_id` / `odoo_invoice_no`
- `thirdparty_invoice_no`
- `gross_amount` / `net_amount` / `tax_amount`
- `invoice_odoo_status` (draft/posted/cancel)
- `invoice_zatka_status` (ZATCA EDI status)
- `qr_code` (ZATCA QR code)

---

## Error Handling

All endpoints return JSON with `status` field:
- `"status": "success"` - Operation completed
- `"status": "error"` - Check `message` field for details

Common errors:
- `Token has expired` - Re-authenticate
- `InvoiceNo is exist` - Duplicate invoice reference
- `Store Is Wrong` - Invalid store ID
