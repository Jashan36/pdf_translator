"""Local PDF Localizer — Streamlit entry point.

Milestone 1 (PDF Forensics): upload a PDF, analyze it with PyMuPDF, and
show the extracted structure (pages, text blocks, fonts, sizes, colors,
bounding boxes, images) as both a readable table and raw JSON.

No translation happens yet — see Section 42 / Section 69 of
local_pdf_localizer_technical_master_plan.md for why this comes first:
we must prove we understand a PDF's visual structure before we attempt
to translate and reconstruct it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pymupdf as fitz
import streamlit as st

from core.pdf.analyzer import analyze_pdf, is_native_text_pdf

st.set_page_config(page_title="Local PDF Localizer", page_icon="[PDF]", layout="wide")

st.title("Local PDF Localizer")
st.caption("Milestone 1 — PDF Forensics (analysis only, no translation yet)")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is None:
    st.info("Upload a PDF to inspect its structure.")
    st.stop()

# PyMuPDF needs a real file path; write the upload to a temp file.
with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = tmp.name

try:
    with fitz.open(tmp_path) as fitz_doc:
        native_text = is_native_text_pdf(fitz_doc)

    if native_text:
        st.success("Detected: native text PDF (Class A) — highest-fidelity path.")
    else:
        st.warning(
            "Detected: little/no extractable text (Class B — likely scanned). "
            "OCR is a later phase (Section 48); results below may be sparse."
        )

    document = analyze_pdf(tmp_path)
finally:
    Path(tmp_path).unlink(missing_ok=True)

st.subheader("Document metadata")
meta_cols = st.columns(4)
meta_cols[0].metric("Pages", document.metadata.page_count)
meta_cols[1].metric("Title", document.metadata.title or "—")
meta_cols[2].metric("Author", document.metadata.author or "—")
meta_cols[3].metric("Producer", document.metadata.producer or "—")

st.subheader("Pages")
page_numbers = [p.page_number for p in document.pages]
selected_page = st.selectbox("Inspect page", page_numbers)
page = next(p for p in document.pages if p.page_number == selected_page)

col_geom, col_counts = st.columns(2)
with col_geom:
    st.markdown("**Geometry**")
    st.write(
        {
            "width": round(page.width, 2),
            "height": round(page.height, 2),
            "rotation": page.rotation,
        }
    )
with col_counts:
    st.markdown("**Object counts**")
    st.write(
        {
            "blocks": len(page.blocks),
            "text_spans": len(page.source_spans),
            "images": len(page.images),
            "drawings": len(page.drawings),
        }
    )

st.markdown("**Blocks (reading order)**")
if page.blocks:
    st.dataframe(
        [
            {
                "order": b.reading_order,
                "type": b.block_type.value,
                "text": b.raw_text[:80],
                "lines": len(b.lines),
                "bbox": f"({b.bbox.x0:.0f}, {b.bbox.y0:.0f}, {b.bbox.x1:.0f}, {b.bbox.y1:.0f})",
            }
            for b in page.blocks
        ],
        use_container_width=True,
        height=250,
    )
else:
    st.write("No blocks on this page.")

st.markdown("**Text spans (span-level)**")
spans = page.source_spans
if spans:
    st.dataframe(
        [
            {
                "order": s.source_order,
                "text": s.text,
                "font": s.style.font_name,
                "size": round(s.style.font_size, 1),
                "bold": s.style.bold,
                "italic": s.style.italic,
                "color": f"#{s.style.color:06x}",
                "bbox": f"({s.bbox.x0:.0f}, {s.bbox.y0:.0f}, {s.bbox.x1:.0f}, {s.bbox.y1:.0f})",
                "rotation": s.rotation,
            }
            for s in spans
        ],
        use_container_width=True,
        height=350,
    )
else:
    st.write("No extractable text spans on this page.")

st.markdown("**Images**")
if page.images:
    st.dataframe(
        [
            {
                "id": img.image_id,
                "bbox": f"({img.bbox.x0:.0f}, {img.bbox.y0:.0f}, {img.bbox.x1:.0f}, {img.bbox.y1:.0f})",
                "xref": img.xref,
                "size": f"{img.width}x{img.height}" if img.width else "—",
            }
            for img in page.images
        ],
        use_container_width=True,
    )
else:
    st.write("No images on this page.")

st.subheader("Full internal document model (JSON)")
with st.expander("Show raw JSON (all pages)"):
    st.json(document.model_dump(mode="json"))

st.download_button(
    "Download document model as JSON",
    data=document.model_dump_json(indent=2),
    file_name=f"{Path(uploaded_file.name).stem}_analysis.json",
    mime="application/json",
)
