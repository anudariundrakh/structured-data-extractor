"""Non-executable excerpts retained for the AI audit discussion.

These snippets represent problems identified in the first baseline draft and are
kept only so the before/after corrections can be demonstrated in the video.
"""

# ISSUE 1 — Pydantic v1 syntax in a Pydantic v2 assignment:
# from pydantic import validator
# @validator("quantity")
# def quantity_positive(cls, value): ...
# data = invoice.dict()

# ISSUE 2 — Context stuffing on every retry:
# retry_prompt = f"SOURCE={entire_multi_page_document}\nERROR={validation_error}"

# ISSUE 3 — Unsafe fallback returning partially valid data:
# except ValidationError:
#     return {"invoice_number": None, "line_items": [], "total_amount": None}
