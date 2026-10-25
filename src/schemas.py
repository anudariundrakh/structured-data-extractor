from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


TOLERANCE = 0.02


class LineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    line_total: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_line_total(self) -> "LineItem":
        expected = self.quantity * self.unit_price
        if abs(expected - self.line_total) > TOLERANCE:
            raise ValueError(
                f"line_total {self.line_total:.2f} does not match "
                f"quantity * unit_price ({expected:.2f})"
            )
        return self


class InvoiceExtraction(BaseModel):
    invoice_number: str = Field(min_length=1, pattern=r"^[A-Za-z0-9._/-]+$")
    vendor_name: str = Field(min_length=2)
    invoice_date: date
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: float = Field(ge=0)
    tax_amount: float = Field(ge=0)
    total_amount: float = Field(gt=0)
    currency: Literal["USD", "EUR", "GBP"]

    @model_validator(mode="after")
    def reconcile_totals(self) -> "InvoiceExtraction":
        item_sum = sum(item.line_total for item in self.line_items)
        if abs(item_sum - self.subtotal) > TOLERANCE:
            raise ValueError(
                f"subtotal {self.subtotal:.2f} does not match line-item total {item_sum:.2f}"
            )

        expected_total = self.subtotal + self.tax_amount
        if abs(expected_total - self.total_amount) > TOLERANCE:
            raise ValueError(
                f"total_amount {self.total_amount:.2f} does not match "
                f"subtotal + tax ({expected_total:.2f})"
            )
        return self


class ExtractionResult(BaseModel):
    validated_data: InvoiceExtraction | None = None
    attempts_used: int = Field(ge=1)
    error_log: list[str] = Field(default_factory=list)
    execution_status: Literal["SUCCESS", "REPAIRED_VIA_REFLECTION", "DLQ_FAILED"]
    audit_log: list[str] = Field(default_factory=list)
    corrective_prompts: list[str] = Field(default_factory=list)
