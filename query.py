"""Running queries against the flight database."""
from validator import is_valid_datetime

RECORD_KEYS = {"flight_id", "origin", "destination",
               "departure_datetime", "arrival_datetime", "price"}
MATCH_KEYS = ("flight_id", "origin", "destination")
RANGE_KEYS = ("price", "min_price")
DATETIME_KEYS = ("departure_datetime", "arrival_datetime")
SORT_KEYS = ("asc", "desc")


def _is_number(value) -> bool:
    """True for int/float values; booleans are not numbers here."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_valid_query(query) -> bool:
    """Check every key and value, including 'order requires sort_by'."""
    if not isinstance(query, dict):
        return False
    for key, value in query.items():
        if key in MATCH_KEYS:
            if not isinstance(value, str):
                return False
        elif key in DATETIME_KEYS:
            if not isinstance(value, str) or not is_valid_datetime(value):
                return False
        elif key in RANGE_KEYS:
            if not _is_number(value):
                return False
        elif key == "sort_by":
            if not isinstance(value, str) or value not in RECORD_KEYS:
                return False
        elif key == "order":
            if not isinstance(value, str) or value not in SORT_KEYS:
                return False
        elif key == "limit":
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return False
        else:
            return False
    if "order" in query and "sort_by" not in query:
        return False
    return True


def _matches(record: dict, query: dict) -> bool:
    """True when the record passes every filter condition (AND)."""
    for key in MATCH_KEYS:
        if key in query and record.get(key) != query[key]:
            return False
    # Datetime filters: both sides are in exact YYYY-MM-DD HH:MM form,
    # so lexicographic order equals chronological order.
    if "departure_datetime" in query:
        if record.get("departure_datetime", "") < query["departure_datetime"]:
            return False
    if "arrival_datetime" in query:
        if record.get("arrival_datetime", "") > query["arrival_datetime"]:
            return False
    if "price" in query and record.get("price") is not None:
        if not record["price"] <= query["price"]:
            return False
    if "min_price" in query and record.get("price") is not None:
        if not record["price"] >= query["min_price"]:
            return False
    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not _is_valid_query(query):
        return {"query": query, "error": "INVALID_QUERY", "matches": []}
    matches = [record for record in db if _matches(record, query)]
    sort_by = query.get("sort_by")
    if sort_by is not None:
        reverse = query.get("order", "asc") == "desc"
        # sorted() with reverse=True keeps database order among equal keys.
        matches = sorted(matches, key=lambda record: record[sort_by], reverse=reverse)
    limit = query.get("limit")
    if limit is not None:
        matches = matches[:limit]
    return {"query": query, "matches": matches}


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, dict):
        queries = [queries]
    elif not isinstance(queries, list):
        queries = [queries]
    return [run_query(db, query) for query in queries]
