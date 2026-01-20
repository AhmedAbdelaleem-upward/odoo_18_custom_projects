# Bashraheel Invoice Integration - Usage Guide

This guide details the complete workflow for installing, configuring, and using the Bashraheel Invoice Integration module to manage ZATCA-compliant e-invoicing via API.

## 1. Installation

**Prerequisite:** Ensure the `custom/Bashraheel` folder is present in your Odoo addons path.

### Steps:
1.  Log in to your Odoo instance as an Administrator.
2.  Go to **Apps**.
3.  Search for **"Bashraheel FastAPI Invoice Integration"** (`bashraheel_fastapi`).
4.  Click **Activate/Install**.
    *   *Note: This will automatically install the core `bashraheel_invoice_integration` module and all required dependencies (FastAPI, JWT Auth, etc.).*

---

## 2. Configuration

### 2.1. Configure Authentication
1.  Go to **Settings > Technical > Auth JWT > Providers**.
2.  Ensure a provider named `bashraheel_jwt` exists (created automatically).
3.  Verify the **Secret Key** matches the one used by your external system.

### 2.2. Set Up Integration User (Optional but Recommended)
1.  Go to **Settings > Users & Companies > Users**.
2.  Create a new user (e.g., "POS Integration User").
3.  Grant strict access rights (e.g., Invoicing User).
4.  Set the **Default Company** to the company issuing invoices.

### 2.3. Configure API Endpoint in Odoo
1.  Go to **FastAPI > FastAPI Endpoints**.
2.  Open **"Bashraheel Invoice API"**.
3.  In the **User** field, select the "POS Integration User" you created.
    *   *Importance: All API actions (creating invoices, refunds) will be performed as this user.*
4.  Set **Auth Method** to "JWT Authentication".

### 2.4. Configure Journals (Store Mapping)
1.  Go to **Invoicing > Configuration > Journals**.
2.  Open your Sales Journal (e.g., "POS Store 001").
3.  Go to the **"Third-Party Integration"** tab (located after "Advanced Settings").
4.  Enter the **Third-Party Store ID** (e.g., `STORE001`).
    *   *This ID links the `store.id` sent in the API JSON to this specific Odoo journal.*

---

## 3. Workflow: Using the API

### 3.1. Authentication (Get Token)
Before calling any other endpoint, you must obtain a JWT access token.

**Endpoint:** `POST /api/v1/auth/login`
**Payload:**
```json
{
  "login": "admin",
  "password": "your_password"
}
```
**Response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUz...",
    "expires_in": 3600
  }
}
```
*Save the `access_token` for subsequent requests.*

### 3.2. Create Invoice
Send sales data from your POS to Odoo.

**Endpoint:** `POST /api/v1/invoice/create`
**Headers:** `Authorization: Bearer <your_access_token>`
**Payload:**
```json
{
  "invoiceList": [{
    "invoiceNo": "POS-INV-001",
    "move_type": "out_invoice",
    "documentDate": "2025-02-15",
    "thirdparty_sa_confirmation_datetime": "2025-02-15 10:30:00",
    "store": {"id": "STORE001"},
    "lines": [
      {"skuCode": "ITEM-A", "qty": 1, "sellingPrice": 100.0, "discount": 0}
    ]
  }]
}
```

### 3.3. Create Refund (Credit Note)
Process returns using the specific return endpoint.

**Endpoint:** `POST /api/v1/invoice/create-return`
**Headers:** `Authorization: Bearer <your_access_token>`

**Partial Refund:**
```json
{
  "invoiceList": [{
    "invoiceNo": "RET-001",
    "main_invoiceNo": "POS-INV-001",
    "move_type": "out_refund",
    "out_refund_type": "partial",
    "documentDate": "2025-02-16",
    "store": {"id": "STORE001"},
    "lines": [
       {"skuCode": "ITEM-A", "qty": 1, "sellingPrice": 100.0}
    ]
  }]
}
```

**Full Refund:**
```json
{
  "invoiceList": [{
    "invoiceNo": "RET-FULL-001",
    "main_invoiceNo": "POS-INV-001",
    "move_type": "out_refund",
    "out_refund_type": "full",
    "documentDate": "2025-02-16",
    "store": {"id": "STORE001"},
    "lines": [{"skuCode": "DUMMY", "qty": 1, "sellingPrice": 0}]
  }]
}
```

### 3.4. Query Report
Check the status of invoices and get ZATCA details (QR Code, Status, Hash).

**Endpoint:** `POST /api/v1/invoice/report`
**Headers:** `Authorization: Bearer <your_access_token>`
**Payload:**
```json
{
  "store_id": "STORE001",
  "date": "2025-02-15"
}
```

**Response Example:**
```json
{
  "status": "success",
  "data": [
    {
      "odoo_invoice_id": 102,
      "odoo_invoice_no": "POS1/2025/00123",
      "thirdparty_invoice_no": "POS-INV-001",
      "gross_amount": 100.0,
      "tax_amount": 15.0,
      "net_amount": 115.0,
      "invoice_odoo_status": "posted",
      "invoice_zatka_status": "Reported",
      "qr_code": "ARdTYXVka..."
    }
  ]
}
```

## 4. Troubleshooting
    - **"Product with SKU not found":** Ensure a Product exists in Odoo with the `Internal Reference` (default_code) matching the `skuCode`.
- **"InvoiceNo is exist":** You are sending a duplicate `invoiceNo`.
- **"Token has expired":** Re-authenticate using the `/auth/login` endpoint.
