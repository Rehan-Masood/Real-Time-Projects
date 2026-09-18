import io
import os
import re
from typing import List

import pandas as pd
import pdfplumber

try:
    import pytesseract
    from PIL import Image
    OCR_PYTHON_AVAILABLE = True
except Exception:
    OCR_PYTHON_AVAILABLE = False

ALIASES = {
    "employee_no": "employee_id",
    "emp_no": "employee_id",
    "emp_id": "employee_id",
    "employee_number": "employee_id",
    "employee_name": "name",
    "full_name": "name",
    "email_address": "email",
    "e_mail": "email",
    "phone_number": "phone",
    "mobile_number": "phone",
    "dept": "department",
    "job_title": "designation",
    "job": "designation",
    "monthly_salary": "salary",
    "basic_salary": "basic_salary",
    "joining_date": "joining_date",
    "date_of_joining": "joining_date",
}

def normalize_header(value):
    value = "" if value is None else str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return ALIASES.get(value, value or "column")

def unique_headers(values):
    seen = {}
    result = []
    for value in values:
        base = normalize_header(value)
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append(base if count == 0 else f"{base}_{count + 1}")
    return result

def _table_to_df(table):
    if not table or len(table) < 2:
        return pd.DataFrame()

    rows = []
    for row in table:
        row = ["" if cell is None else str(cell).strip() for cell in (row or [])]
        if any(row):
            rows.append(row)

    if len(rows) < 2:
        return pd.DataFrame()

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = unique_headers(rows[0])

    # Ignore tables that are obviously not data tables.
    if len(header) < 2:
        return pd.DataFrame()

    return pd.DataFrame(rows[1:], columns=header)

def _text_table_to_df(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        else:
            parts = [p.strip() for p in re.split(r"\s{2,}", line)]
        if len(parts) >= 2:
            rows.append(parts)

    if len(rows) < 2:
        return pd.DataFrame()

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    return pd.DataFrame(rows[1:], columns=unique_headers(rows[0]))

def _tesseract_command():
    configured = os.getenv("TESSERACT_CMD")
    if configured:
        return configured
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None

def _configure_tesseract():
    if not OCR_PYTHON_AVAILABLE:
        return False
    cmd = _tesseract_command()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

def _ocr_dataframe(page):
    if not _configure_tesseract():
        return pd.DataFrame(), "Tesseract executable was not found. Set TESSERACT_CMD locally or install tesseract-ocr."

    try:
        image = page.to_image(resolution=250).original
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DATAFRAME,
            config="--psm 6",
        )
        data = data.dropna(subset=["text"])
        data["text"] = data["text"].astype(str).str.strip()
        data = data[data["text"].ne("")]
        if data.empty:
            return pd.DataFrame(), "OCR returned no text."

        # Build OCR lines using Tesseract's page/block/paragraph/line identifiers.
        groups = []
        for _, group in data.groupby(["block_num", "par_num", "line_num"], sort=False):
            group = group.sort_values("left")
            words = []
            for _, row in group.iterrows():
                words.append({
                    "text": str(row["text"]),
                    "left": float(row["left"]),
                    "right": float(row["left"] + row["width"]),
                })
            groups.append(words)

        if len(groups) < 2:
            return pd.DataFrame(), "OCR found text but not enough table-like rows."

        # A simple, layout-aware table reconstruction:
        # large horizontal gaps become column boundaries.
        row_values = []
        for words in groups:
            values = []
            for i, word in enumerate(words):
                value = word["text"]
                if i > 0:
                    gap = word["left"] - words[i - 1]["right"]
                    if gap > 35:
                        values.append("|")
                values.append(value)
            line = " ".join(values)
            parts = [x.strip() for x in line.split("|") if x.strip()]
            if len(parts) >= 2:
                row_values.append(parts)

        if len(row_values) < 2:
            return pd.DataFrame(), "OCR found text but could not infer multiple columns."

        width = max(len(row) for row in row_values)
        # Avoid accidentally treating very short prose as a table.
        if width < 2:
            return pd.DataFrame(), "OCR output is not table-shaped."

        row_values = [row + [""] * (width - len(row)) for row in row_values]
        return pd.DataFrame(row_values[1:], columns=unique_headers(row_values[0])), ""

    except Exception as exc:
        return pd.DataFrame(), f"OCR failed on page {page.page_number}: {exc}"

def _remove_repeated_headers(df):
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    for col in df.columns:
        mask &= df[col].astype(str).str.strip().str.lower().ne(str(col).lower())
    return df.loc[mask].reset_index(drop=True)

def extract_employee_data(pdf_bytes: bytes):
    frames = []
    methods = []
    warnings = []
    ocr_pages = 0

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = len(pdf.pages)

        for page in pdf.pages:
            # 1. Native PDF tables.
            native = []
            try:
                native = [
                    df for table in page.extract_tables()
                    if not (df := _table_to_df(table)).empty
                ]
            except Exception as exc:
                warnings.append(f"Page {page.page_number}: table extraction warning: {exc}")

            if native:
                frames.extend(native)
                methods.extend(["pdf_table"] * len(native))
                continue

            # 2. Native text that looks tabular.
            text = page.extract_text() or ""
            text_df = _text_table_to_df(text)
            if not text_df.empty:
                frames.append(text_df)
                methods.append("pdf_text")
                continue

            # 3. OCR fallback for scanned/image pages.
            ocr_pages += 1
            ocr_df, ocr_warning = _ocr_dataframe(page)
            if not ocr_df.empty:
                frames.append(ocr_df)
                methods.append("ocr")
            elif ocr_warning:
                warnings.append(f"Page {page.page_number}: {ocr_warning}")

    if not frames:
        return {
            "dataframe": pd.DataFrame(),
            "method": "none",
            "pages": pages,
            "ocr_pages": ocr_pages,
            "warnings": warnings + [
                "No structured rows were detected. Complex forms, merged cells, handwriting, or highly unusual layouts may require a custom parser."
            ],
        }

    df = pd.concat(frames, ignore_index=True, sort=False).fillna("")
    df = _remove_repeated_headers(df)
    df = df.drop_duplicates().reset_index(drop=True)

    # Remove completely empty columns.
    keep = [c for c in df.columns if df[c].astype(str).str.strip().ne("").any()]
    df = df[keep]

    unique_methods = list(dict.fromkeys(methods))
    method = unique_methods[0] if len(unique_methods) == 1 else "mixed"

    return {
        "dataframe": df,
        "method": method,
        "pages": pages,
        "ocr_pages": ocr_pages,
        "warnings": warnings,
    }
