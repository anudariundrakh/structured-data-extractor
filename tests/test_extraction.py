from datetime import date

import pytest
from pydantic import ValidationError

from src.providers import DemoInvoiceProvider
from src.schemas import InvoiceExtraction, LineItem


def valid_invoice() -> dict:
    return {
        "invoice_number": "INV-1001",
        "vendor_name": "Acme Supplies",
        "invoice_date": date(2026, 10, 12),
        "line_items": [
            {
                "description": "Keyboard",
                "quantity": 2,
                "unit_price": 50.0,
                "line_total": 100.0,
            }
        ],
        "subtotal": 100.0,
        "tax_amount": 10.0,
        "total_amount": 110.0,
        "currency": "USD",
    }


def test_golden_document_schema_passes():
    invoice = InvoiceExtraction.model_validate(valid_invoice())
    assert invoice.invoice_number == "INV-1001"
    assert invoice.total_amount == 110.0


def test_schema_rejects_zero_quantity():
    data = valid_invoice()
    data["line_items"][0]["quantity"] = 0
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(data)


def test_cross_field_reconciliation_rejects_bad_total():
    data = valid_invoice()
    data["total_amount"] = 999.0
    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate(data)


def test_line_item_rejects_bad_line_total():
    with pytest.raises(ValidationError):
        LineItem(description="Mouse", quantity=2, unit_price=20.0, line_total=70.0)


def test_demo_provider_extracts_sample_invoice():
    raw_text = """
Vendor: Northstar Office Supply
Invoice Number: INV-2026-1042
Invoice Date: October 12, 2026
Currency: USD
ITEM: Ergonomic Office Chair | QTY: 5 | UNIT: $199.99 | LINE: $999.95
ITEM: LED Desk Lamp | QTY: 10 | UNIT: $19.95 | LINE: $199.50
ITEM: Shipping | QTY: 1 | UNIT: $50.05 | LINE: $50.05
Subtotal: $1,249.50
Tax: $126.20
Grand Total: $1,375.70
"""
    payload = DemoInvoiceProvider().extract(raw_text)
    invoice = InvoiceExtraction.model_validate(payload)
    assert len(invoice.line_items) == 3
    assert invoice.total_amount == 1375.70
