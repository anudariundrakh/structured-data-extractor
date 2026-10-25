from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .fallback import build_reflection_prompt, try_json_repair, write_dlq
from .providers import StructuredProvider
from .schemas import ExtractionResult, InvoiceExtraction


class SchemaExtractor:
    def __init__(
        self,
        provider: StructuredProvider,
        *,
        max_retries: int = 3,
        dlq_path: str | Path = "data/dlq.jsonl",
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        self.provider = provider
        self.max_retries = max_retries
        self.dlq_path = Path(dlq_path)

    def extract_with_retry(
        self,
        raw_text: str,
        *,
        enable_reflection: bool = True,
    ) -> ExtractionResult:
        error_log: list[str] = []
        audit_log: list[str] = []
        corrective_prompts: list[str] = []
        last_payload: Any = None

        for attempt in range(1, self.max_retries + 1):
            corrective_prompt = corrective_prompts[-1] if attempt > 1 and corrective_prompts else None
            audit_log.append(f"Attempt {attempt}: requesting structured invoice output")

            try:
                last_payload = self.provider.extract(raw_text, corrective_prompt)
                parsed = try_json_repair(last_payload)
                if parsed is None:
                    raise ValueError("Provider returned non-JSON output that could not be repaired")

                invoice = InvoiceExtraction.model_validate(parsed)
                status = "SUCCESS" if attempt == 1 else "REPAIRED_VIA_REFLECTION"
                audit_log.append(f"Attempt {attempt}: Pydantic validation passed")
                return ExtractionResult(
                    validated_data=invoice,
                    attempts_used=attempt,
                    error_log=error_log,
                    execution_status=status,
                    audit_log=audit_log,
                    corrective_prompts=corrective_prompts,
                )
            except (ValidationError, ValueError) as exc:
                message = str(exc)
                error_log.append(f"Attempt {attempt}: {message}")
                audit_log.append(f"Attempt {attempt}: validation failed")

                if not enable_reflection:
                    break

                if attempt < self.max_retries:
                    prompt = build_reflection_prompt(raw_text, last_payload, message)
                    corrective_prompts.append(prompt)
                    audit_log.append(
                        f"Attempt {attempt}: created targeted corrective prompt for next attempt"
                    )

        # Stage 3: best-effort syntax repair is attempted, but semantic schema rules are never bypassed.
        repaired = try_json_repair(last_payload)
        if repaired is not None:
            try:
                invoice = InvoiceExtraction.model_validate(repaired)
                audit_log.append("Heuristic JSON repair produced schema-valid data")
                return ExtractionResult(
                    validated_data=invoice,
                    attempts_used=max(1, min(self.max_retries, len(error_log))),
                    error_log=error_log,
                    execution_status="REPAIRED_VIA_REFLECTION",
                    audit_log=audit_log,
                    corrective_prompts=corrective_prompts,
                )
            except ValidationError as exc:
                error_log.append(f"Heuristic repair validation failed: {exc}")

        dlq_file = write_dlq(self.dlq_path, raw_text, last_payload, error_log)
        audit_log.append(f"Routed irrecoverable payload to DLQ: {dlq_file}")
        return ExtractionResult(
            validated_data=None,
            attempts_used=max(1, min(self.max_retries, len([e for e in error_log if e.startswith('Attempt')]))),
            error_log=error_log,
            execution_status="DLQ_FAILED",
            audit_log=audit_log,
            corrective_prompts=corrective_prompts,
        )
