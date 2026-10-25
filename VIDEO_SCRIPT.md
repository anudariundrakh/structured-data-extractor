# 5–7 Minute Video Script / Cue Sheet

## 0:00–1:00 — Architecture and schema
Hi, my name is Anudari Undrakh. This project is a resilient unstructured invoice extraction pipeline. A user provides PDF, HTML, or text. The application extracts the text, asks an LLM for structured invoice data, validates the output with Pydantic v2, and either returns validated JSON or enters a bounded reflection retry loop. If all repair attempts fail, the payload is routed to a dead-letter queue instead of crashing the application.

In `schemas.py`, I have a nested `LineItem` model and an `InvoiceExtraction` model. Quantity and unit price must be positive. Each line total must match quantity times unit price within a two-cent tolerance. At the invoice level, the subtotal must equal the line-item total, and the grand total must equal subtotal plus tax.

## 1:00–2:30 — AI audit
I used an AI assistant to create the baseline draft, but I treated the output as untrusted code and audited it.

The first issue was Pydantic version mixing. The baseline used patterns associated with Pydantic v1, such as `@validator` and `.dict()`. I corrected the implementation to Pydantic v2 using `@model_validator` and `.model_dump()`.

The second issue was context stuffing in retries. A naive retry can resend the entire document every time, which increases token cost and latency. I changed the reflection prompt so it only includes a limited source context, the previous payload, and the exact Pydantic validation error.

I also made sure failed validation never returns a half-empty object. If the data cannot pass the schema after bounded attempts, it goes to the DLQ.

## 2:30–4:00 — Live extraction
Now I’ll run the Streamlit app. I can upload a document or use the included messy HTML invoice. When I run extraction, the app parses the raw data and displays the validated JSON next to the source document. The output includes the invoice number, vendor, date, line items, subtotal, tax, total, and currency.

The reconciliation checks confirm that the line items add up correctly and that the grand total matches subtotal plus tax.

## 4:00–5:30 — Reflection and DLQ
Next I’ll click `Simulate Reflection Repair`. The first generated payload intentionally contains an invalid currency and incorrect total. Pydantic rejects it, the application captures the exact validation error, creates a corrective reflection prompt, and retries. The second attempt succeeds, so the final status is `REPAIRED_VIA_REFLECTION`.

Now I’ll click `Simulate Edge Case Failure`. This provider keeps returning invalid data. After the maximum number of attempts, the app stops retrying and writes the failed record to the dead-letter queue. The application remains running and the UI shows `DLQ_FAILED`, which is safer than silently accepting bad data or crashing.

## 5:30–6:15 — Tests and summary
Finally, I’ll run `pytest -v`. The tests cover a valid invoice, invalid quantities, cross-field reconciliation, reflection recovery, and DLQ routing.

The main lesson from this project is that LLM output should never be trusted directly. Structured decoding, Pydantic validation, bounded retries, audit logs, and a DLQ create a much more reliable production pipeline. Thank you.
