"""Spreadsheet export hardening.

Values typed by the public into our forms end up in CSV/XLSX files that staff
open in Excel or LibreOffice. A cell starting with =, +, - or @ is parsed as a
formula by those programs, so an unauthenticated visitor could plant a DDE
payload (=cmd|\'/C calc\'!A0) or an exfiltration formula (=HYPERLINK(...)) that
runs on a committee member\'s machine. Neutralise it at export time.
"""

import re


# Characters that make Excel/LibreOffice treat a cell as a formula
_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

# Values that merely *start* with + or - but are plain numbers or phone numbers
# ("+57 300 1234567", "-15") are harmless and must stay readable.
_NUMERIC_LIKE = re.compile(r'^[+-]?[\d\s().\-]+$')


def sanitize_spreadsheet_value(value):
    """Return `value` safe to place in a spreadsheet cell.

    Non-strings pass through untouched. Strings that would be parsed as a
    formula get an apostrophe prefix, which Excel and LibreOffice both read as
    "treat the rest as literal text".
    """
    if not isinstance(value, str) or not value:
        return value
    if not value.startswith(_FORMULA_PREFIXES):
        return value
    if _NUMERIC_LIKE.match(value):
        return value
    return "\'" + value
