"""Reading CSV files into flight records and error messages."""
import csv
import os

from validator import to_record, validate_row


def parse_files(paths: list[str], airports: set[str]) -> tuple[list[dict], list[str]]:
    """Process the CSV files in the order given.

    Return (records, errors):
      records - valid flight records, in input order
      errors  - one message per invalid row, in input order, formatted as
                "<file name>:<line number>: <ERROR_CODE> | <free text>"
                (base file name only, no timestamp or level, no newline)

    Also performs the DUPLICATE_FLIGHT check across all the files.
    Does not write any files and does not log anything itself.
    """
    records: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()

    for path in paths:
        file_name = os.path.basename(path)
        with open(path, encoding="utf-8-sig") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                if line_no == 1:
                    continue  # header: always skipped, never validated
                line = raw_line.rstrip("\n")
                if not line.strip():
                    continue  # blank line: skip
                if line.lstrip().startswith("#"):
                    continue  # comment line: skip
                fields = next(csv.reader([line]))
                error = validate_row(fields, airports)
                if error is None:
                    record = to_record(fields)
                    key = (record["flight_id"], record["departure_datetime"])
                    if key in seen:
                        errors.append(
                            f"{file_name}:{line_no}: DUPLICATE_FLIGHT | {line.strip()}")
                    else:
                        seen.add(key)
                        records.append(record)
                else:
                    errors.append(f"{file_name}:{line_no}: {error} | {line.strip()}")
    return records, errors
