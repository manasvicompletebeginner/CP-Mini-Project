"""
validators.py - Input validation helpers.

UNIT III (Regular Expressions + Dates):
  * re.compile() patterns validate usernames, room codes, amounts and dates.
  * re.split() parses a comma-separated list of custom shares.
  * datetime.strptime() checks a date is real (e.g. rejects 2026-02-30),
    and timedelta limits how far in the future a date can be.

UNIT I: functions with default and keyword arguments (field=..., minimum=...).
"""
import re
from datetime import date, datetime, timedelta

from .exceptions import InvalidRoomCodeError, ValidationError

USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,19}$")       # 3-20 chars, starts with a letter
ROOM_CODE_PATTERN = re.compile(r"^[A-Z0-9]{6}$")               # exactly 6 uppercase alphanumerics
AMOUNT_PATTERN = re.compile(r"^\d{1,7}(\.\d{1,2})?$")          # up to 2 decimal places
PEOPLE_PATTERN = re.compile(r"^\d{1,2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")              # YYYY-MM-DD
TEXT_PATTERN = re.compile(r"^[\w\s&'.,!()\-#/]+$")             # letters, digits, common punctuation
SHARES_PATTERN = re.compile(r"^\s*\d+(\.\d{1,2})?(\s*,\s*\d+(\.\d{1,2})?)*\s*$")

MAX_FUTURE_DAYS = 365


def validate_username(value):
    username = str(value or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError(
            "Username must be 3-20 characters: letters, digits or _, starting with a letter."
        )
    return username


def validate_room_code(value):
    code = str(value or "").strip().upper()
    if not ROOM_CODE_PATTERN.fullmatch(code):
        raise InvalidRoomCodeError()
    return code


def validate_amount(value, field="Total amount", minimum=1.0):
    text = str(value if value is not None else "").strip()
    if not AMOUNT_PATTERN.fullmatch(text):
        raise ValidationError(f"{field} must be a number with at most 2 decimals.")
    amount = float(text)
    if amount < minimum:
        raise ValidationError(f"{field} must be at least ₹{minimum:.0f}.")
    return round(amount, 2)


def validate_people(value, minimum=2, maximum=50):
    text = str(value if value is not None else "").strip()
    if not PEOPLE_PATTERN.fullmatch(text):
        raise ValidationError("Total people must be a whole number.")
    people = int(text)
    if not minimum <= people <= maximum:
        raise ValidationError(f"Total people must be between {minimum} and {maximum} (including you).")
    return people


def validate_date(value):
    text = str(value or "").strip()
    if not DATE_PATTERN.fullmatch(text):
        raise ValidationError("Date must be in YYYY-MM-DD format.")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{text} is not a real calendar date.")
    if parsed > date.today() + timedelta(days=MAX_FUTURE_DAYS):
        raise ValidationError("Date cannot be more than a year in the future.")
    return parsed.isoformat()


def validate_text(value, field="Text", required=True, max_length=40):
    text = re.sub(r"\s+", " ", str(value or "")).strip()   # collapse repeated spaces
    if not text:
        if required:
            raise ValidationError(f"{field} is required.")
        return ""
    if len(text) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    if not TEXT_PATTERN.fullmatch(text):
        raise ValidationError(f"{field} contains characters that are not allowed.")
    return text


def parse_custom_shares(value):
    """'200, 150.5,100' -> [200.0, 150.5, 100.0]"""
    if isinstance(value, (list, tuple)):
        value = ",".join(str(v) for v in value)
    text = str(value or "")
    if not SHARES_PATTERN.fullmatch(text):
        raise ValidationError("Custom shares must be numbers separated by commas, e.g. 300, 250, 250.")
    return [round(float(part), 2) for part in re.split(r"\s*,\s*", text.strip())]
