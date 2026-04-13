"""
SEC-007: CSV Injection sanitization helper.

Prevents spreadsheet formula injection by escaping values that start
with characters interpreted as formulas by Excel, LibreOffice, and
Google Sheets (=, +, -, @, TAB, CR, LF).

Usage:
    from apps.core.utils.csv_sanitize import sanitize_csv_value

    writer.writerow([sanitize_csv_value(v) for v in row])
"""

import re

# Characters that trigger formula execution in spreadsheet applications
_FORMULA_CHARS = re.compile(r"^[=+\-@\t\r\n]")


def sanitize_csv_value(value: object) -> str:
    """Sanitize a value for safe CSV export.

    Prefixes dangerous characters with a single quote to prevent
    spreadsheet applications from interpreting them as formulas.

    Args:
        value: Any value to be written to CSV.

    Returns:
        Sanitized string safe for CSV export.
    """
    if value is None:
        return ""
    s = str(value)
    if _FORMULA_CHARS.match(s):
        return f"'{s}"
    return s
