import re
import pandas as pd

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def clean_and_validate(df):
    data = df.copy()
    data.columns = [str(c).strip() for c in data.columns]

    for col in data.columns:
        data[col] = data[col].map(lambda value: "" if pd.isna(value) else str(value).strip())

    for salary_col in ["salary", "basic_salary", "gross_salary", "net_salary", "allowance", "tax"]:
        if salary_col in data.columns:
            data[salary_col] = (
                data[salary_col]
                .str.replace(r"(?i)(rs\.?|pkr|₨)\s*", "", regex=True)
                .str.replace(",", "", regex=False)
                .str.strip()
            )

    duplicate_rows = []
    if "employee_id" in data.columns:
        mask = data["employee_id"].duplicated(keep=False) & data["employee_id"].ne("")
        duplicate_rows = data.index[mask].tolist()

    invalid_email_rows = []
    if "email" in data.columns:
        for idx, value in data["email"].items():
            if value and not EMAIL_RE.match(value):
                invalid_email_rows.append(idx)

    missing_required_rows = []
    required = [c for c in ["employee_id", "name"] if c in data.columns]
    for idx, row in data.iterrows():
        if required and any(not str(row[c]).strip() for c in required):
            missing_required_rows.append(idx)

    issues = []
    if "employee_id" not in data.columns:
        issues.append("Required column 'employee_id' was not detected.")
    if "name" not in data.columns:
        issues.append("Required column 'name' was not detected.")
    if duplicate_rows:
        issues.append(f"{len(duplicate_rows)} row(s) contain duplicate employee IDs.")
    if invalid_email_rows:
        issues.append(f"{len(invalid_email_rows)} email value(s) look invalid.")
    if missing_required_rows:
        issues.append(f"{len(missing_required_rows)} row(s) have missing required values.")

    valid_mask = pd.Series(True, index=data.index)
    if missing_required_rows:
        valid_mask.loc[missing_required_rows] = False

    return data.reset_index(drop=True), {
        "duplicate_rows": duplicate_rows,
        "invalid_email_rows": invalid_email_rows,
        "missing_required_rows": missing_required_rows,
        "valid_rows": int(valid_mask.sum()),
        "issues": issues,
    }
