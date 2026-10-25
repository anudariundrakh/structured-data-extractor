from __future__ import annotations

from io import BytesIO


def extract_text_from_upload(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if lower.endswith((".html", ".htm")):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "html.parser")
        return soup.get_text("\n", strip=True)

    return content.decode("utf-8", errors="replace")
