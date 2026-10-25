from pathlib import Path

from src.extractor import SchemaExtractor
from src.providers import HardFailureDemoProvider, ReflectionDemoProvider


SAMPLE = """
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


def test_reflection_loop_self_heals_on_attempt_two(tmp_path: Path):
    result = SchemaExtractor(
        ReflectionDemoProvider(), max_retries=3, dlq_path=tmp_path / "dlq.jsonl"
    ).extract_with_retry(SAMPLE)

    assert result.execution_status == "REPAIRED_VIA_REFLECTION"
    assert result.attempts_used == 2
    assert result.validated_data is not None
    assert result.validated_data.currency == "USD"
    assert len(result.corrective_prompts) == 1


def test_hard_failure_routes_to_dlq(tmp_path: Path):
    dlq = tmp_path / "dlq.jsonl"
    result = SchemaExtractor(
        HardFailureDemoProvider(), max_retries=3, dlq_path=dlq
    ).extract_with_retry("totally unusable source")

    assert result.execution_status == "DLQ_FAILED"
    assert result.validated_data is None
    assert result.attempts_used == 3
    assert dlq.exists()
    assert "DLQ_FAILED" in dlq.read_text(encoding="utf-8")
