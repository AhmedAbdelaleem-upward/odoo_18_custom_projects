# -*- coding: utf-8 -*-

from typing import List, Optional, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, field_serializer


# ============ Invoice Line Schemas ============

class InvoiceLineRequest(BaseModel):
    """Schema for a single invoice line item"""
    skuCode: str = Field(..., description="Product SKU code")
    skuid: Optional[str] = Field(None, description="Product SKU ID")
    qty: float = Field(..., gt=0, description="Quantity (must be > 0)")
    sellingPrice: float = Field(..., ge=0, description="Selling price per unit")
    discount: float = Field(default=0, ge=0, le=100, description="Discount percentage (0-100)")


# ============ Store Schema ============

class StoreInfo(BaseModel):
    """Schema for store information"""
    id: str = Field(..., description="Store identifier")


# ============ Invoice Request Schemas ============

class InvoiceRequest(BaseModel):
    """Schema for a single invoice in the request"""
    invoiceNo: str = Field(..., description="Third-party invoice number (unique)")
    move_type: str = Field(..., pattern="^(out_invoice|out_refund)$", description="Invoice type")
    documentDate: str = Field(..., description="Document date (YYYY-MM-DD)")
    thirdparty_sa_confirmation_datetime: Optional[str] = Field(
        None, description="Confirmation datetime from third-party (YYYY-MM-DD HH:MM:SS)"
    )
    store: Optional[StoreInfo] = Field(None, description="Store information (required for out_invoice)")
    lines: List[InvoiceLineRequest] = Field(..., min_length=1, description="Invoice line items")
    main_invoiceNo: Optional[str] = Field(None, description="Original invoice number (required for refunds)")
    out_refund_type: Optional[str] = Field(
        None, pattern="^(full|partial)$", description="Refund type (required for refunds)"
    )


class CreateInvoiceRequest(BaseModel):
    """Schema for creating invoices (batch)"""
    invoiceList: List[InvoiceRequest] = Field(..., min_length=1, description="List of invoices to create")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoiceList": [{
                        "invoiceNo": "INV-001",
                        "move_type": "out_invoice",
                        "documentDate": "2025-02-15",
                        "thirdparty_sa_confirmation_datetime": "2025-02-15 10:30:00",
                        "store": {"id": "STORE001"},
                        "lines": [
                            {"skuCode": "FURN_0001", "qty": 2, "sellingPrice": 100.0, "discount": 0}
                        ]
                    }]
                },
                {
                    "invoiceList": [{
                        "invoiceNo": "REF-001",
                        "main_invoiceNo": "INV-001",
                        "move_type": "out_refund",
                        "out_refund_type": "partial",
                        "documentDate": "2025-02-16",
                        "thirdparty_sa_confirmation_datetime": "2025-02-16 11:00:00",
                        "store": {"id": "STORE001"},
                        "lines": [
                            {"skuCode": "FURN_0001", "qty": 1, "sellingPrice": 100.0, "discount": 0}
                        ]
                    }]
                },
                {
                    "invoiceList": [{
                        "invoiceNo": "REF-002",
                        "main_invoiceNo": "INV-001",
                        "move_type": "out_refund",
                        "out_refund_type": "full",
                        "documentDate": "2025-02-16",
                        "thirdparty_sa_confirmation_datetime": "2025-02-16 11:00:00",
                        "store": {"id": "STORE001"},
                        "lines": [
                            {"skuCode": "DUMMY", "qty": 1, "sellingPrice": 0, "discount": 0}
                        ]
                    }]
                }
            ]
        }
    }


# ============ Invoice Response Schemas ============

class InvoiceCreatedData(BaseModel):
    """Schema for successfully created invoice data"""
    id: int = Field(..., description="Odoo invoice ID")
    qr_code: Optional[str] = Field(None, description="ZATCA QR code")
    odoo_invoice_no: str = Field(..., description="Odoo-generated invoice number")


class SingleInvoiceResponse(BaseModel):
    """Schema for a single invoice creation result"""
    status: str = Field(..., description="success or error")
    data: Optional[InvoiceCreatedData] = Field(None, description="Invoice data if successful")
    message: Optional[str] = Field(None, description="Error message if failed")


class CreateInvoiceResponse(BaseModel):
    """Schema for batch invoice creation response"""
    status: str = Field(..., description="Overall status: success or error")
    data: Optional[List[SingleInvoiceResponse]] = Field(None, description="List of invoice results")
    message: Optional[str] = Field(None, description="Error message if overall failure")


# ============ Report Request/Response Schemas ============

class ReportInvoicesRequest(BaseModel):
    """Schema for querying invoices"""
    store_id: str = Field(..., description="Store identifier")
    date: str = Field(..., description="Invoice date (YYYY-MM-DD)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"store_id": "STORE001", "date": "2025-02-15"}
            ]
        }
    }


class InvoiceReportItem(BaseModel):
    """Schema for a single invoice in the report"""
    odoo_invoice_id: int = Field(..., description="Odoo invoice ID")
    odoo_invoice_no: str = Field(..., description="Odoo invoice number")
    thirdparty_invoice_no: Optional[str] = Field(None, description="Third-party invoice number")
    gross_amount: float = Field(..., description="Amount before tax")
    net_amount: float = Field(..., description="Total amount including tax")
    tax_amount: float = Field(..., description="Tax amount")
    invoice_date: Any = Field(..., description="Invoice date")
    l10n_sa_confirmation_datetime: Any = Field(None, description="ZATCA confirmation datetime")
    invoice_odoo_status: str = Field(..., description="Odoo invoice status (draft/posted/cancel)")
    invoice_zatka_status: Any = Field(None, description="ZATCA EDI status")
    qr_code: Any = Field(None, description="ZATCA QR code")
    store_id: Optional[str] = Field(None, description="Store identifier")

    @field_serializer('invoice_date')
    def serialize_invoice_date(self, v):
        if isinstance(v, date):
            return v.isoformat()
        return v if v else None

    @field_serializer('l10n_sa_confirmation_datetime')
    def serialize_confirmation_datetime(self, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v if v else None

    @field_serializer('invoice_zatka_status')
    def serialize_zatka_status(self, v):
        return v if v else None

    @field_serializer('qr_code')
    def serialize_qr_code(self, v):
        return v if v else None


class ReportInvoicesResponse(BaseModel):
    """Schema for invoice report response"""
    status: str = Field(..., description="success or error")
    data: Optional[List[InvoiceReportItem]] = Field(None, description="List of invoices")
    message: Optional[str] = Field(None, description="Error message if failed")
