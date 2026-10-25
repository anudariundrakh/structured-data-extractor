from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractor import SchemaExtractor
from src.parsers import extract_text_from_upload
from src.providers import (
    DemoInvoiceProvider,
    HardFailureDemoProvider,
    OpenAIProvider,
    ReflectionDemoProvider,
)


load_dotenv()

st.set_page_config(page_title="Resilient Invoice Extractor", layout="wide")
st.title("Resilient Unstructured Data Extractor")
st.caption("Pydantic v2 validation • reflection self-correction • DLQ fallback")

with st.sidebar:
    st.header("Settings")
    provider_name = st.selectbox("Provider", ["Local Demo", "OpenAI Structured Outputs"])
    enable_reflection = st.toggle("Enable reflection self-correction", value=True)
    max_retries = st.slider("Max attempts", min_value=1, max_value=5, value=3)

uploaded = st.file_uploader("Upload PDF, HTML, or text", type=["pdf", "html", "htm", "txt"])
manual_text = st.text_area("Or paste raw invoice text/HTML", height=180)

raw_text = manual_text
if uploaded is not None:
    raw_text = extract_text_from_upload(uploaded.name, uploaded.getvalue())

sample_path = Path("samples/invoice_messy.html")
if not raw_text and sample_path.exists():
    st.info("No document uploaded yet. Click 'Load sample invoice' to use the included messy HTML sample.")
    if st.button("Load sample invoice"):
        st.session_state["sample_text"] = sample_path.read_text(encoding="utf-8")
        st.rerun()

if st.session_state.get("sample_text") and not raw_text:
    raw_text = st.session_state["sample_text"]

left, right = st.columns(2)
with left:
    st.subheader("Raw document")
    st.text_area("Source", value=raw_text, height=360, label_visibility="collapsed")


def render_result(result):
    with right:
        st.subheader("Validated output")
        if result.validated_data:
            st.json(result.validated_data.model_dump(mode="json"))
            if result.execution_status == "SUCCESS":
                st.success("SUCCESS — valid on first attempt")
            else:
                st.warning("REPAIRED VIA REFLECTION — invalid first output was corrected")
        else:
            st.error("DLQ_FAILED — input could not be safely validated")

        st.metric("Attempts used", result.attempts_used)
        st.write("**Execution status:**", result.execution_status)

    st.subheader("Audit log")
    for entry in result.audit_log:
        st.code(entry)

    if result.error_log:
        with st.expander("Validation errors"):
            for error in result.error_log:
                st.text(error)

    if result.corrective_prompts:
        with st.expander("Corrective reflection prompts"):
            for index, prompt in enumerate(result.corrective_prompts, start=1):
                st.markdown(f"**Prompt {index}**")
                st.code(prompt)


button_col1, button_col2, button_col3 = st.columns(3)

with button_col1:
    if st.button("Run extraction", type="primary", use_container_width=True):
        if not raw_text.strip():
            st.error("Upload a document or paste invoice text first.")
        else:
            if provider_name == "OpenAI Structured Outputs":
                if not os.getenv("OPENAI_API_KEY"):
                    st.error("Set OPENAI_API_KEY in .env before using the OpenAI provider.")
                    st.stop()
                provider = OpenAIProvider()
            else:
                provider = DemoInvoiceProvider()

            result = SchemaExtractor(provider, max_retries=max_retries).extract_with_retry(
                raw_text, enable_reflection=enable_reflection
            )
            render_result(result)

with button_col2:
    if st.button("Simulate Reflection Repair", use_container_width=True):
        source = raw_text or sample_path.read_text(encoding="utf-8")
        result = SchemaExtractor(ReflectionDemoProvider(), max_retries=3).extract_with_retry(
            source, enable_reflection=True
        )
        render_result(result)

with button_col3:
    if st.button("Simulate Edge Case Failure (DLQ)", use_container_width=True):
        source = raw_text or "irrecoverable nonsense payload"
        result = SchemaExtractor(HardFailureDemoProvider(), max_retries=3).extract_with_retry(
            source, enable_reflection=True
        )
        render_result(result)
