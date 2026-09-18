import io
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from core.pdf_extractor import extract_employee_data
from core.data_cleaner import clean_and_validate
from core.template_engine import inspect_template
from core.document_generator import generate_documents
from core.pdf_converter import convert_docx_directory_to_pdf, office_available
from core.zip_generator import make_zip
from utils.helpers import dataframe_to_excel_bytes

st.set_page_config(
    page_title="MailFlow — PDF Mail Merge",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"] { font-family: "DM Sans", sans-serif; }
.stApp {
    background:
      radial-gradient(circle at 12% 5%, rgba(255,196,72,.10), transparent 27%),
      radial-gradient(circle at 88% 8%, rgba(41,211,180,.08), transparent 25%),
      linear-gradient(135deg,#070c0f 0%,#0b1316 50%,#111419 100%);
}
.block-container { max-width: 1450px; padding-top: 1.8rem; padding-bottom: 4rem; }
.hero {
    padding: 30px 34px; border: 1px solid rgba(255,255,255,.08);
    border-radius: 26px; background: rgba(255,255,255,.035);
    box-shadow: 0 20px 70px rgba(0,0,0,.25); margin-bottom: 24px;
}
.brand { color:#ffd477; font-weight:800; letter-spacing:.14em; font-size:.76rem; }
.hero h1 { font-family:"Space Grotesk"; font-size:2.65rem; margin:.35rem 0 .45rem; letter-spacing:-.055em; }
.hero p { color:#aab6b8; max-width:900px; line-height:1.7; margin:0; }
.card,.metric {
    border:1px solid rgba(255,255,255,.075); border-radius:19px;
    background:rgba(255,255,255,.028); padding:20px; margin-bottom:16px;
}
.metric .n { font-family:"Space Grotesk"; font-size:1.7rem; font-weight:700; }
.metric .l { color:#91a0a2; font-size:.78rem; margin-top:3px; }
.step { padding:10px 13px; border-radius:10px; margin:6px 0; color:#98a5a7; border:1px solid rgba(255,255,255,.06); }
.step.active { color:#f4f6f6; border-color:rgba(255,196,72,.30); background:rgba(255,196,72,.055); }
.small { color:#91a0a2; font-size:.82rem; }
[data-testid="stFileUploaderDropzone"] { border-radius:14px; }
.stButton > button, .stDownloadButton > button { border-radius:11px; font-weight:700; min-height:42px; }
</style>
""", unsafe_allow_html=True)

def metric(label, value):
    st.markdown(
        f'<div class="metric"><div class="n">{value}</div><div class="l">{label}</div></div>',
        unsafe_allow_html=True,
    )

def reset_workspace():
    for key in list(st.session_state.keys()):
        if key.startswith(("mf_", "records", "template", "generated", "validation", "extraction")):
            del st.session_state[key]

if "records" not in st.session_state:
    st.session_state.records = None
if "generated" not in st.session_state:
    st.session_state.generated = None

with st.sidebar:
    st.markdown("## ✦ MailFlow")
    st.caption("PDF → Data → DOCX → PDF")
    st.divider()
    for no, label in [
        ("01", "Upload & detect"),
        ("02", "Validate & review"),
        ("03", "Template mapping"),
        ("04", "Generate & export"),
    ]:
        active = (
            (no == "01" and st.session_state.records is None)
            or (no == "02" and st.session_state.records is not None and not st.session_state.get("template_path"))
            or (no == "03" and st.session_state.get("records") is not None and not st.session_state.get("generated"))
            or (no == "04" and st.session_state.get("generated") is not None)
        )
        st.markdown(
            f'<div class="step {"active" if active else ""}"><b>{no}</b>&nbsp;&nbsp;{label}</div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.caption("Local development + Streamlit Community Cloud")
    st.caption("No API key is required.")
    if st.button("Reset workspace", use_container_width=True):
        reset_workspace()
        st.rerun()

st.markdown("""
<div class="hero">
  <div class="brand">AUTOMATED DOCUMENT OPERATIONS</div>
  <h1>PDF Mail Merge Automation</h1>
  <p>Detect the PDF type, extract structured records or OCR scanned pages, validate and edit the data, merge it into a Word template, convert to PDF, and download the complete package.</p>
</div>
""", unsafe_allow_html=True)

# STEP 1
st.markdown("## 01 · Upload & detect")
pdf_file = st.file_uploader(
    "Employee records PDF",
    type=["pdf"],
    help="Digital/table PDFs use pdfplumber. Pages without usable text/table data automatically fall back to OCR.",
)

if pdf_file and st.button("Analyze PDF & Extract Records", type="primary", use_container_width=True):
    with st.spinner("Detecting PDF type and extracting records..."):
        try:
            result = extract_employee_data(pdf_file.getvalue())
            st.session_state.records = result["dataframe"]
            st.session_state.extraction = result
            st.session_state.validation = None
            st.session_state.template_path = None
            st.session_state.generated = None
            if result["dataframe"].empty:
                st.error("No structured records could be detected. See the extraction diagnostics below.")
            else:
                st.success(
                    f"Detected {len(result['dataframe'])} records and {len(result['dataframe'].columns)} columns."
                )
        except Exception as exc:
            st.error(f"Extraction failed: {exc}")

if st.session_state.records is not None:
    df = st.session_state.records.copy()
    meta = st.session_state.get("extraction", {})

    st.markdown("### Extraction diagnostics")
    c = st.columns(5)
    values = [
        ("Records", len(df)),
        ("Columns", len(df.columns)),
        ("Pages", meta.get("pages", "—")),
        ("OCR pages", meta.get("ocr_pages", 0)),
        ("Method", str(meta.get("method", "—")).upper()),
    ]
    for col, (label, value) in zip(c, values):
        with col:
            metric(label, value)

    if meta.get("warnings"):
        with st.expander("Extraction warnings & diagnostics"):
            for warning in meta["warnings"]:
                st.write("•", warning)

    st.markdown("## 02 · Validate & review")
    st.caption("Columns are discovered dynamically. You can edit cells, add rows, or remove rows before mail merge.")

    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        height=430,
        key="employee_editor",
    )
    st.session_state.records = edited

    cleaned, report = clean_and_validate(edited)
    st.session_state.validation = report

    c = st.columns(4)
    for col, (label, value) in zip(c, [
        ("Rows", len(edited)),
        ("Valid rows", report["valid_rows"]),
        ("Duplicate IDs", len(report["duplicate_rows"])),
        ("Email warnings", len(report["invalid_email_rows"])),
    ]):
        with col:
            metric(label, value)

    if report["issues"]:
        with st.expander("Validation issues", expanded=True):
            for issue in report["issues"]:
                st.warning(issue)
    else:
        st.success("Data quality checks passed.")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download CSV",
            edited.to_csv(index=False).encode("utf-8-sig"),
            "employee_data.csv",
            "text/csv",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download Excel",
            dataframe_to_excel_bytes(edited),
            "employee_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # STEP 3
    st.markdown("## 03 · Template mapping")
    st.caption("Create a DOCX template with placeholders such as {{ name }}, {{ department }}, {{ salary }}.")
    template_file = st.file_uploader(
        "Word mail-merge template (.docx)",
        type=["docx"],
        key="template_upload",
    )

    if template_file:
        if st.button("Inspect template fields", use_container_width=True):
            try:
                info = inspect_template(template_file.getvalue())
                st.session_state.template_info = info
                st.session_state.template_bytes = template_file.getvalue()
                st.success(f"Found {len(info['fields'])} template fields.")
            except Exception as exc:
                st.error(f"Template inspection failed: {exc}")

    if st.session_state.get("template_info"):
        info = st.session_state.template_info
        columns = [str(c) for c in edited.columns]
        missing = [field for field in info["fields"] if field not in columns]

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Field mapping")
        st.dataframe(
            pd.DataFrame({
                "Template field": info["fields"],
                "Data column": [field if field in columns else "NOT FOUND" for field in info["fields"]],
                "Status": ["Matched" if field in columns else "Missing" for field in info["fields"]],
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if missing:
            st.error("These placeholders do not exist in the extracted columns: " + ", ".join(missing))
        elif st.button("Save template & continue", type="primary", use_container_width=True):
            workdir = Path(tempfile.mkdtemp(prefix="mailflow_"))
            template_path = workdir / "template.docx"
            template_path.write_bytes(st.session_state.template_bytes)
            st.session_state.template_path = str(template_path)
            st.session_state.workdir = str(workdir)
            st.session_state.generated = None
            st.success("Template is ready for preview or batch generation.")

    # STEP 4
    if st.session_state.get("template_path"):
        st.markdown("## 04 · Generate & export")
        p1, p2 = st.columns(2)
        with p1:
            preview_clicked = st.button("Generate 1-record preview", use_container_width=True)
        with p2:
            batch_clicked = st.button("Generate all documents", type="primary", use_container_width=True)

        if preview_clicked or batch_clicked:
            records = st.session_state.records.copy()
            subset = records.head(1) if preview_clicked else records
            workdir = Path(st.session_state.workdir)
            docx_dir = workdir / ("preview_docx" if preview_clicked else "docx")
            pdf_dir = workdir / ("preview_pdf" if preview_clicked else "pdf")
            if docx_dir.exists():
                shutil.rmtree(docx_dir)
            if pdf_dir.exists():
                shutil.rmtree(pdf_dir)

            progress = st.progress(0)
            status = st.empty()

            try:
                result = generate_documents(
                    Path(st.session_state.template_path),
                    subset,
                    docx_dir,
                    progress_callback=lambda done, total: (
                        progress.progress(done / total if total else 1),
                        status.write(f"Generating document {done} of {total}...")
                    ),
                )

                pdf_result = convert_docx_directory_to_pdf(docx_dir, pdf_dir)
                final_dir = pdf_dir if pdf_result["converted"] else docx_dir

                zip_path = workdir / ("mailflow_preview.zip" if preview_clicked else "mailflow_output.zip")
                make_zip(final_dir, zip_path)

                st.session_state.generated = {
                    "zip_path": str(zip_path),
                    "success": result["success"],
                    "failed": result["failed"],
                    "pdf_converted": pdf_result["converted"],
                    "notes": pdf_result["notes"],
                }
                status.empty()
                progress.empty()
                st.success(
                    f"Completed: {len(result['success'])} successful, {len(result['failed'])} failed."
                )
            except Exception as exc:
                st.error(f"Generation failed: {exc}")

# RESULTS
if st.session_state.generated:
    result = st.session_state.generated
    st.markdown("### Results")
    c = st.columns(3)
    for col, (label, value) in zip(c, [
        ("Successful", len(result["success"])),
        ("Failed", len(result["failed"])),
        ("Output", "PDF" if result["pdf_converted"] else "DOCX"),
    ]):
        with col:
            metric(label, value)

    if result["failed"]:
        with st.expander("Failed records"):
            st.dataframe(pd.DataFrame(result["failed"]), use_container_width=True, hide_index=True)

    if result["notes"]:
        st.caption(result["notes"])

    with open(result["zip_path"], "rb") as fh:
        st.download_button(
            "Download complete ZIP package",
            fh.read(),
            Path(result["zip_path"]).name,
            "application/zip",
            type="primary",
            use_container_width=True,
        )

st.markdown("---")
st.caption("MailFlow Automation · detect → extract/OCR → validate → review → merge → PDF → ZIP")
