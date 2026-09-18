from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

def make_zip(source_dir, zip_path):
    source_dir = Path(source_dir)
    zip_path = Path(zip_path)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for file in source_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(source_dir))
    return zip_path
