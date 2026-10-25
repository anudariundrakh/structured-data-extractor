# AI Prompt Log and Human Verification

## 1. Baseline generation prompt

I used an AI coding assistant to draft the initial implementation with this prompt:

> You are a Staff AI Systems Engineer specializing in reliable programmatic LLM integration. Build a Python 3.11+ invoice extraction application that reads PDF/HTML text, requests structured JSON from an LLM, validates it with Pydantic v2, retries on ValidationError using the exact error trace, and sends irrecoverable payloads to a dead-letter queue. Include a Streamlit UI and pytest tests. Keep the output split across schemas.py, extractor.py, fallback.py, and app.py.

The baseline was then reviewed manually before being accepted.

## 2. Audit finding #1 — Pydantic v1/v2 collision

**Problem found:** The baseline used examples resembling Pydantic v1 (`@validator` and `.dict()`), while the assignment requires Pydantic v2.

**Why it matters:** Mixing major-version syntax can cause runtime errors or silently use outdated validation patterns.

**Fix:** The final code uses `@model_validator(mode="after")` for cross-field validation and `.model_dump()` for serialization. See `src/schemas.py`.

## 3. Audit finding #2 — Context stuffing in reflection retries

**Problem found:** The first retry design would resend the full source document together with every previous output and error.

**Why it matters:** Large repeated contexts waste tokens, increase latency/cost, and can amplify untrusted document content during retries.

**Fix:** `src/fallback.py` caps source context at 6,000 characters and sends only the previous payload plus the exact validation error. This creates a targeted corrective prompt rather than blindly duplicating the entire document.

## 4. Audit finding #3 — Unsafe fallback behavior

**Problem found:** A naive fallback could catch validation failures and return half-empty objects so the application keeps running.

**Why it matters:** That would defeat deterministic schema enforcement and could send invalid records downstream.

**Fix:** The final pipeline never marks a record successful unless `InvoiceExtraction.model_validate()` passes. If all attempts fail, it writes an auditable JSONL record to `data/dlq.jsonl` with status `DLQ_FAILED`.

## 5. Additional verification

- Positive quantities and prices are enforced.
- Each line total is reconciled against `quantity * unit_price` within a 0.02 tolerance.
- Invoice subtotal is reconciled against line-item totals.
- Grand total is reconciled against subtotal + tax.
- Currency is limited to `USD`, `EUR`, or `GBP`.
- Retry count is bounded to prevent infinite loops/API-cost runaway.
- The test suite covers success, schema rejection, cross-field failure, reflection recovery, and DLQ routing.

## 6. Human decision

The AI-generated baseline was treated as an untrusted draft. The final implementation was accepted only after schema checks, retry-bounds review, failure-path review, and automated tests passed.
