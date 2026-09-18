import re
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
def is_email(value): return bool(EMAIL_RE.match(str(value or "")))
