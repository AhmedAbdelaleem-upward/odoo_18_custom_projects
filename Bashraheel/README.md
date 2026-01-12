# Bashraheel Odoo 18 Modules

Custom Odoo 18 modules for invoice integration with ZATCA (Saudi Arabia e-invoicing) via FastAPI.

## Modules

| Module | Description |
|--------|-------------|
| `bashraheel_invoice_integration` | Core invoice integration with ZATCA e-invoicing |
| `bashraheel_fastapi` | FastAPI REST endpoints for third-party POS integration |
| `simple_api` | Simple API utilities |

## Requirements

### System Dependencies
```bash
sudo apt install postgresql libpq-dev libldap2-dev libsasl2-dev build-essential python3-dev wkhtmltopdf -y
```

### Python Dependencies
```bash
pip install -r requirements.txt
```

### OCA Dependencies
Clone these OCA repositories (branch 18.0):
```bash
git clone -b 18.0 https://github.com/OCA/rest-framework.git
git clone -b 18.0 https://github.com/OCA/web-api.git
git clone -b 18.0 https://github.com/OCA/server-auth.git
```

## Installation

1. Add the following paths to your Odoo `addons_path`:
   ```
   addons_path = /path/to/odoo/addons,
       /path/to/custom/Bashraheel,
       /path/to/custom/OCA/rest-framework,
       /path/to/custom/OCA/web-api,
       /path/to/custom/OCA/server-auth
   ```

2. Install the main module:
   ```bash
   ./odoo-bin -c your_config.conf -i bashraheel_invoice_integration
   ```

3. `bashraheel_fastapi` will auto-install when `fastapi` (from OCA) is also installed.

## API Endpoints

Once installed, the FastAPI endpoints are available at:

| Endpoint | Description |
|----------|-------------|
| `/api/v1/docs` | Swagger UI documentation |
| `/api/v1/redoc` | ReDoc documentation |
| `/api/v1/auth/login` | JWT authentication |
| `/api/v1/invoice/create` | Create invoice from POS |
| `/api/v1/invoice/create-return` | Create return/refund invoice |
| `/api/v1/invoice/report` | Query invoice status |

## Configuration

After installation, go to **FastAPI > FastAPI Endpoint** and click **"Sync Registry"** to register all API routes.

## License

LGPL-3
