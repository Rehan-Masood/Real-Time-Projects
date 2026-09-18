from pathlib import Path
import pandas as pd
from docxtpl import DocxTemplate

from utils.helpers import safe_filename

def generate_documents(template_path, dataframe, output_dir, progress_callback=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    success, failed = [], []
    total = len(dataframe)

    for n, (_, row) in enumerate(dataframe.iterrows(), start=1):
        try:
            context = {
                str(column): ("" if pd.isna(value) else str(value))
                for column, value in row.to_dict().items()
            }

            doc = DocxTemplate(str(template_path))
            doc.render(context)

            employee_id = context.get("employee_id") or str(n)
            name = context.get("name") or f"employee_{n}"
            filename = safe_filename(f"{employee_id}_{name}.docx")
            path = output_dir / filename
            doc.save(str(path))

            success.append({
                "employee_id": employee_id,
                "name": name,
                "file": filename,
            })
        except Exception as exc:
            failed.append({"row": n, "error": str(exc)})

        if progress_callback:
            progress_callback(n, total)

    return {"success": success, "failed": failed}
