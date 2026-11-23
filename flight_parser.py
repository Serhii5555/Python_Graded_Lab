"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# Student details: plain ASCII, no spaces or underscores.
STUDENT_ID = "260ADB195"
FIRST_NAME = "Serhii"
LAST_NAME = "Beilakh"

logger = logging.getLogger("flight_parser")


class LabError(Exception):
    """A runtime problem that must end the program with exit code 1."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flight_parser",
        description="Flight Schedule Parser and Query Tool")
    parser.add_argument("-i", dest="input_file", metavar="FILE",
                        help="parse a single CSV file")
    parser.add_argument("-d", dest="input_dir", metavar="FOLDER",
                        help="parse every .csv file in the folder (not sub-folders)")
    parser.add_argument("-j", dest="json_db", metavar="FILE",
                        help="load an existing JSON database")
    parser.add_argument("-a", dest="airports_file", metavar="FILE",
                        help="airport list file (required with -i and -d)")
    parser.add_argument("-o", dest="output_file", metavar="FILE",
                        help="output path for the JSON database (default: db.json)")
    parser.add_argument("-q", dest="query_file", metavar="FILE",
                        help="run the queries in this JSON file")
    parser.add_argument("-r", dest="response_dir", metavar="FOLDER", default=".",
                        help="folder for the query response file (default: current directory)")
    return parser


def _load_json(path: str):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _print_error(message: str) -> None:
    """Print one clean 'Error: ...' line to stderr, always ASCII-safe.

    An OSError message can quote a path with characters that the current
    stdio encoding cannot represent (for example a non-ASCII Windows user
    name in a temp folder path). Encoding must never turn an expected
    error into a traceback, and non-ASCII bytes in stderr can also break
    a caller that decodes the pipe with a legacy code page, so the line
    is always written with non-ASCII characters escaped.
    """
    line = f"Error: {message}\n"
    sys.stderr.write(line.encode("ascii", "backslashreplace").decode("ascii"))


def _log_errors(log_path: str, errors: list[str]) -> None:
    """Write every error message to errors.log.

    One WARNING line per invalid row and nothing else. The handler is always
    removed and closed, even if logging raises, so that a later run in the
    same process starts from a clean logger.
    """
    logger.setLevel(logging.INFO)
    logger.propagate = False  # never echo the rows to a root console handler
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    try:
        for message in errors:
            logger.warning(message)
    finally:
        logger.removeHandler(handler)
        handler.close()


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2).

    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this by default).
    Do not call sys.exit() inside main(); return the code instead.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)

        # ---------------- usage checks (exit code 2) ----------------
        sources = [s for s in (args.input_file, args.input_dir, args.json_db) if s]
        if not sources:
            parser.error("exactly one data source (-i, -d or -j) is required")
        if len(sources) > 1:
            parser.error("-i, -d and -j are mutually exclusive")
        if args.json_db and args.output_file:
            parser.error("-o is only allowed with -i or -d")
        parsing = bool(args.input_file or args.input_dir)
        if parsing and not args.airports_file:
            parser.error("-a is required with -i and -d")

        # ---------------- load or parse the data ----------------
        if parsing:
            if args.input_file:
                paths = [args.input_file]
            else:
                if not os.path.isdir(args.input_dir):
                    raise LabError(f"folder does not exist: {args.input_dir}")
                names = sorted(n for n in os.listdir(args.input_dir)
                               if n.endswith(".csv")
                               and os.path.isfile(os.path.join(args.input_dir, n)))
                if not names:
                    raise LabError(f"no .csv files found in {args.input_dir}")
                paths = [os.path.join(args.input_dir, n) for n in names]

            airports = load_airports(args.airports_file)
            db, errors = parse_files(paths, airports)

            out_path = args.output_file or "db.json"
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(db, handle, indent=2)
                handle.write("\n")
            _log_errors(os.path.join(os.path.dirname(os.path.abspath(out_path)),
                                     "errors.log"), errors)
            print(f"Parsed {len(paths)} file(s): {len(db)} valid flight(s), "
                  f"{len(errors)} invalid row(s).")
        else:
            db = _load_json(args.json_db)
            if not isinstance(db, list) or not all(isinstance(r, dict) for r in db):
                raise LabError(
                    f"database file is not a JSON array of objects: {args.json_db}")

        # ---------------- optional queries ----------------
        if args.query_file:
            queries = _load_json(args.query_file)
            if isinstance(queries, dict):
                query_list = [queries]
            elif isinstance(queries, list):
                query_list = queries
            else:
                raise LabError(
                    f"query file is not a JSON object or an array: {args.query_file}")
            if not all(isinstance(q, dict) for q in query_list):
                raise LabError(
                    f"every query must be a JSON object: {args.query_file}")

            responses = run_queries(db, queries)
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            name = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{stamp}.json"
            response_path = os.path.join(args.response_dir, name)
            with open(response_path, "w", encoding="utf-8") as handle:
                json.dump(responses, handle, indent=2)
                handle.write("\n")
            print(f"Wrote {len(responses)} response entry/entries to {name}.")
        return 0
    except SystemExit as exc:  # argparse -h (0) and usage errors (2)
        return exc.code if isinstance(exc.code, int) else 2
    except json.JSONDecodeError as exc:
        _print_error(f"not valid JSON: {exc}")
        return 1
    except UnicodeDecodeError as exc:
        _print_error(f"file is not valid UTF-8: {exc}")
        return 1
    except LabError as exc:
        _print_error(str(exc))
        return 1
    except OSError as exc:
        _print_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
