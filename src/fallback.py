from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_CONTEXT_CHARS = 6000


def build_reflection_prompt(
    raw_text: str,
    previous_payload: Any,
    validation_error: str,
) -> str:
    """Build a targeted retry prompt without stuffing the full source document."""
    context = raw_text[:MAX_CONTEXT_CHARS]
    previous_json = json.dumps(previous_payload, ensure_ascii=False, default=str, indent=2)
    return f"""The previous invoice extraction failed strict Pydantic v2 validation.

Correct ONLY the fields necessary to satisfy the schema. Return one corrected JSON object.
Do not invent new line items. Preserve evidence from the source document.

SOURCE CONTEXT (truncated to control token usage):
{context}

PREVIOUS PAYLOAD:
{previous_json}

VALIDATION ERROR:
{validation_error}
"""


def try_json_repair(payload: Any) -> Any | None:
    """Best-effort syntax repair. Schema validation must still pass afterwards."""
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json

        repaired = repair_json(payload, return_objects=True)
        return repaired
    except Exception:
        return None


def write_dlq(
    dlq_path: str | Path,
    raw_text: str,
    last_payload: Any,
    errors: list[str],
) -> Path:
    path = Path(dlq_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DLQ_FAILED",
        "raw_text_preview": raw_text[:2000],
        "last_payload": last_payload,
        "errors": errors,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path
