import shutil
import subprocess

def office_available():
    return bool(shutil.which("libreoffice") or shutil.which("soffice"))

def convert_docx_directory_to_pdf(docx_dir, pdf_dir):
    pdf_dir.mkdir(parents=True, exist_ok=True)
    office = shutil.which("libreoffice") or shutil.which("soffice")

    if not office:
        return {
            "converted": False,
            "notes": "LibreOffice was not found. Generated DOCX files are available. Install LibreOffice locally or use the Linux package in packages.txt on Streamlit Community Cloud.",
        }

    converted = 0
    errors = []

    for docx in docx_dir.glob("*.docx"):
        try:
            subprocess.run(
                [
                    office,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(pdf_dir),
                    str(docx),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            expected = pdf_dir / f"{docx.stem}.pdf"
            if expected.exists():
                converted += 1
            else:
                errors.append(f"{docx.name}: PDF file was not produced.")
        except Exception as exc:
            errors.append(f"{docx.name}: {exc}")

    if converted == 0:
        return {
            "converted": False,
            "notes": "LibreOffice was found but did not produce usable PDFs. Generated DOCX files are available.",
        }

    note = f"Converted {converted} DOCX file(s) to PDF."
    if errors:
        note += f" {len(errors)} file(s) had conversion errors."
    return {"converted": True, "notes": note}
