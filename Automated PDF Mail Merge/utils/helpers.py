import io
import re
import pandas as pd

def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name))
    name = re.sub(r"\s+", "_", name).strip("._ ")
    return name[:150] or "document"

def dataframe_to_excel_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Employees")
    return buffer.getvalue()
