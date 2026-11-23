"""Row validation: airport list loading, single-row checks, record building."""
import math
import re
from datetime import datetime

FLIGHT_ID_RE = re.compile(r"[A-Za-z0-9]{2,8}")
AIRPORT_RE = re.compile(r"[A-Z]{3}")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def load_airports(path: str) -> set[str]:
    """Read an airport list file and return the set of codes.

    One code per line. Strip whitespace; skip blank lines and lines
    starting with '#'.
    """
    codes: set[str] = set()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            code = line.strip()
            if not code or code.startswith("#"):
                continue
            codes.add(code)
    return codes


def is_valid_datetime(value: str) -> bool:
    """True when value is a real date and time in exact YYYY-MM-DD HH:MM form.

    The regex enforces the exact shape (zero-padded, single space) and
    strptime() then rejects dates and times that do not exist.
    """
    if not DATETIME_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, DATETIME_FORMAT)
    except ValueError:
        return False
    return True


def parse_datetime(value: str) -> datetime:
    """Parse a value already known to be in the exact YYYY-MM-DD HH:MM form."""
    return datetime.strptime(value, DATETIME_FORMAT)


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Check one CSV row (fields as returned by csv.reader, not yet stripped).

    Return None if the row is valid, otherwise the error code of the
    FIRST failing check (checks 1-11 in the specification, in order).
    Does not check for duplicates.
    """
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"
    values = [field.strip() for field in fields]
    if any(value == "" for value in values):
        return "MISSING_FIELD"
    flight_id, origin, destination, departure, arrival, price = values

    # 3. flight_id: 2-8 ASCII letters or digits (regex classes are ASCII-only).
    if not FLIGHT_ID_RE.fullmatch(flight_id):
        return "INVALID_FLIGHT_ID"
    # 4./5. airport codes: exactly 3 uppercase ASCII letters, known in the list.
    if not AIRPORT_RE.fullmatch(origin) or origin not in airports:
        return "INVALID_ORIGIN"
    if not AIRPORT_RE.fullmatch(destination) or destination not in airports:
        return "INVALID_DESTINATION"
    # 6.
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"
    # 7./8. exact YYYY-MM-DD HH:MM, and a real date (regex + strptime).
    if not is_valid_datetime(departure):
        return "INVALID_DEPARTURE"
    if not is_valid_datetime(arrival):
        return "INVALID_ARRIVAL"
    # 9.
    if parse_datetime(arrival) <= parse_datetime(departure):
        return "ARRIVAL_NOT_AFTER_DEPARTURE"
    # 10. must convert with float() and be finite (nan, inf rejected).
    try:
        price_value = float(price)
    except ValueError:
        return "INVALID_PRICE"
    if not math.isfinite(price_value):
        return "INVALID_PRICE"
    # 11.
    if price_value <= 0.0:
        return "NON_POSITIVE_PRICE"
    return None


def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary.

    Keys: flight_id, origin, destination, departure_datetime,
    arrival_datetime (stripped strings) and price (float).
    """
    flight_id, origin, destination, departure, arrival, price = [
        field.strip() for field in fields
    ]
    return {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": departure,
        "arrival_datetime": arrival,
        "price": float(price),
    }
