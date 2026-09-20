# MailFlow — PDF Mail Merge Automation

A premium Streamlit application for:

**PDF → Type Detection → Native Table/Text Extraction or OCR → Dynamic Columns → Validation → Review/Edit → DOCX Mail Merge → PDF → ZIP**

## 🔗 Live Demo

**[View Live MailFlow →](https://real-time-projects-zqncakinx2evnywenfqhmk.streamlit.app/)**

## What is improved in this version?

### 1. Automatic PDF type handling
Every page is tried in this order:

1. Native PDF table extraction with `pdfplumber`
2. Native text/table-like extraction
3. OCR fallback with Tesseract for pages that do not yield structured data

A PDF can therefore contain a mixture of normal and scanned pages.

### 2. Dynamic columns
The application does not hard-code a fixed employee schema. It can create different numbers of columns depending on the source data.

For example:

```text
PDF A → employee_id, name, department, salary
PDF B → employee_id, name, department, designation, salary, email, phone, location
PDF C → many additional fields
```

The review grid displays the columns detected from the uploaded document.

### 3. Validation and human review
Before generating official documents, the user can:

- edit extracted cells
- add/remove rows
- inspect duplicate employee IDs
- inspect email warnings
- download CSV/XLSX

### 4. DOCX mail merge
Word templates use placeholders:

```text
{{ employee_id }}
{{ name }}
{{ department }}
{{ designation }}
{{ salary }}
{{ email }}
```

Any detected column can be used as a template field.

### 5. PDF conversion
LibreOffice is used for DOCX → PDF conversion.

### 6. Free deployment
The project is prepared for Streamlit Community Cloud:

- `requirements.txt` = Python dependencies
- `packages.txt` = Linux system dependencies
- `.streamlit/config.toml` = app configuration

## Local Windows setup

Python 3.11 is recommended.

```powershell
cd "D:\PDF-Mail-Merge-Automation"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### Local OCR

`pytesseract` is a Python wrapper. You also need the Tesseract executable on Windows.

If Tesseract is installed at a non-standard path, set:

```powershell
$env:TESSERACT_CMD="C:\Path\To\tesseract.exe"
```

Then start Streamlit in the same terminal.

### Local PDF conversion

Install LibreOffice and make sure `soffice.exe` is on PATH.

Check:

```powershell
where.exe soffice
```

## Create a DOCX template

Example:

```text
EMPLOYEE INFORMATION

Employee ID: {{ employee_id }}
Name: {{ name }}
Department: {{ department }}
Designation: {{ designation }}
Salary: {{ salary }}
Email: {{ email }}
Phone: {{ phone }}
Location: {{ location }}

Dear {{ name }},

This document was generated automatically for employee {{ employee_id }}.

Regards,
HR Department
```

The placeholder names must match the detected data-column names.

## Streamlit Community Cloud deployment

1. Create a GitHub repository.
2. Push the complete project.
3. Do not commit real employee records.
4. Open Streamlit Community Cloud.
5. Connect the GitHub repository.
6. Select `app.py` as the main file.
7. Deploy.

The cloud build reads `requirements.txt` and `packages.txt`.

### Free-hosting reality

The application is deployable on the free Streamlit Community Cloud offering, but free compute, memory, session and execution limits apply. OCR and large batch jobs consume more resources than ordinary text extraction. A 200-record workflow may be practical when the source PDF and templates are reasonably sized, but there is no guarantee that an arbitrarily large or complex workload will fit within a free-hosting resource limit.

Uploaded employee information should be treated as sensitive. Do not commit employee PDFs, spreadsheets, generated documents or secrets to GitHub.

## PDF extraction reality

This project is designed to handle **variable column counts**, but no generic PDF parser can guarantee perfect extraction from every possible visual layout.

Reliable cases:
- normal digital tables
- machine-generated PDFs
- repeated tabular records
- scanned tables that OCR can read clearly

Harder cases:
- merged cells
- multi-column forms
- decorative layouts
- handwriting
- very low-resolution scans
- overlapping text
- fields positioned freely rather than in a table

The application therefore includes a review/edit stage before mail merge.

## Suggested repository

`PDF-Mail-Merge-Automation`

## Architecture

```text
                  PDF
                   │
                   ▼
          ┌─────────────────┐
          │ PDF Type/Content│
          │     Detection   │
          └────────┬────────┘
                   │
             ┌─────┴─────┐
             ▼           ▼
       Text/Table       Scanned
             │           │
             ▼           ▼
         pdfplumber    Tesseract
             │           │
             └─────┬─────┘
                   ▼
          Structured DataFrame
                   │
                   ▼
            Validation/Cleanup
                   │
                   ▼
             Review + Edit
                   │
                   ▼
             DOCX Mail Merge
                   │
                   ▼
             LibreOffice PDF
                   │
                   ▼
                  ZIP
```
