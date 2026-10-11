#!/usr/bin/env python3
"""hematrack — a tiny CLI for tracking personal blood-test (lab) results.

Pure Python standard library, zero dependencies. Store each test as a row of
named markers (e.g. ferritin, ggt, carbamazepine), list them, and print a
trend report that flags values outside reference ranges.

Usage examples:
    hematrack add --date 2026-06-10 --marker ferritin=12.4 --marker ggt=86
    hematrack add --date 2026-10-01 --ferritin 22 --ggt 90 --carbamazepine 6.5 --note "routine"
    hematrack list
    hematrack trends
    hematrack demo
    hematrack --file mydata.json trends
"""

import argparse
import json
import os
import sys
from datetime import date

DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".hematrack", "records.json")

# Reference ranges/limits (value is the "worry" bound). Define per marker as:
#   name -> {"high": value}  (values above HIGH are flagged)
#   name -> {"low": value}   (values below LOW are flagged)
#   name -> {"good_min": l, "good_max": h}  (outside [l, h] is flagged)
# These are sensible illustrative defaults for the common SG lab panel; users
# should adjust to their own lab's reference ranges (or pass --no-ranges).
REFERENCE_RANGES = {
    "ferritin":      {"low": 15},                                  # µg/L (iron stores)
    "ggt":           {"high": 60},                                 # U/L (liver enzyme)
    "carbamazepine": {"good_min": 4, "good_max": 12},              # mg/L therapeutic window
    "hemoglobin":    {"good_min": 120, "good_max": 150},           # g/L
    "mcv":           {"good_min": 80, "good_max": 100},            # fL
}

# Parented names -> friendly descriptions for the trends report.
MARKER_LABELS = {
    "ferritin":      "Ferritin (iron stores)",
    "ggt":           "GGT (liver enzyme)",
    "carbamazepine": "Carbamazepine (therapeutic)",
    "hemoglobin":    "Haemoglobin",
    "mcv":           "MCV (cell size)",
}


def _load(filepath):
    """Return the list of records from `filepath`, or [] if none yet."""
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        print(f"error: corrupt data file {filepath}: {exc}", file=sys.stderr)
        sys.exit(1)


def _save(filepath, records):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, sort_keys=True)
    os.replace(tmp, filepath)


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        print(f"error: bad date '{value}' (use YYYY-MM-DD)", file=sys.stderr)
        sys.exit(1)


def _parse_marker(token):
    """Accept 'name=value' or the shorthand flags --<name> <value> (converted by caller)."""
    if "=" not in token:
        print(f"error: marker '{token}' must be name=value (e.g. ferritin=12.4)",
              file=sys.stderr)
        sys.exit(1)
    name, _, raw = token.partition("=")
    name = name.strip().lower()
    try:
        value = float(raw)
    except ValueError:
        print(f"error: marker '{name}' value '{raw}' is not a number", file=sys.stderr)
        sys.exit(1)
    return name, value


def _format_value(name, value):
    """Pretty-print a number, trimming trailing zeros (12.0 -> 12)."""
    if value == int(value):
        return str(int(value))
    return str(round(value, 2))


def _range_judgement(name, value):
    """Return ("OK", None) or ("FLAG", explanation) for a marker value."""
    r = REFERENCE_RANGES.get(name)
    if not r:
        return None, None
    if "low" in r and value < r["low"]:
        return "FLAG", f"below reference (min {_format_value(name, r['low'])})"
    if "high" in r and value > r["high"]:
        return "FLAG", f"above reference (max {_format_value(name, r['high'])})"
    if "good_min" in r and "good_max" in r and not (r["good_min"] <= value <= r["good_max"]):
        return "FLAG", (f"outside reference range "
                        f"[{_format_value(name, r['good_min'])}–"
                        f"{_format_value(name, r['good_max'])}]")
    return "OK", None


def cmd_add(args, records):
    if not args.marker and not args.shorthand:
        print("error: need at least one --marker name=value", file=sys.stderr)
        sys.exit(1)

    markers = {}
    for token in args.marker:
        name, value = _parse_marker(token)
        markers[name] = value
    for name, value in args.shorthand:
        markers[name.lower()] = value

    if not markers:
        print("error: need at least one marker", file=sys.stderr)
        sys.exit(1)

    when = _parse_date(args.date) if args.date else date.today()
    record = {
        "date": when.isoformat(),
        "markers": markers,
        "note": args.note or "",
    }
    records.append(record)
    records.sort(key=lambda r: r["date"])
    _save(args.filepath, records)
    total = len(records)
    print(f"added record for {when} ({len(markers)} marker(s)); {total} total")


def cmd_list(args, records):
    if not records:
        print("no records yet (try `hematrack demo` or `hematrack add …`)")
        return
    names = sorted({n for r in records for n in r["markers"]})
    header = f"{'DATE':<12}" + "".join(f"{n:>16}" for n in names) + "  NOTE"
    print(header)
    print("-" * len(header))
    for rec in records:
        row = f"{rec['date']:<12}"
        for n in names:
            v = rec["markers"].get(n)
            row += f"{_format_value(n, v) if v is not None else '—':>16}"
        row += "  " + (rec.get("note", "") or "")
        print(row.rstrip())


def cmd_trends(args, records):
    if not records:
        print("no records yet (try `hematrack demo`)")
        return

    names = sorted({n for r in records for n in r["markers"]})
    for name in names:
        # newest first
        history = [(r["date"], r["markers"][name]) for r in records if name in r["markers"]]
        history.sort(key=lambda x: x[0])
        _latest_date, latest = history[-1]

        label = MARKER_LABELS.get(name, name.capitalize())
        line = f"{label:<32} {_format_value(name, latest)}"
        if len(history) >= 2:
            prev_date, prev = history[-2]
            delta = latest - prev
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "=")
            line += f"   ({arrow} {_format_value(name, abs(delta))} vs {prev_date})"

        status, why = _range_judgement(name, latest)
        flag = ""
        if status == "FLAG":
            flag = f"  ⚠ {why}"
        elif status == "OK":
            flag = "  ✓ in range"
        if flag:
            line += flag
        print(line)

    print()
    print("Ranges: " + ", ".join(
        f"{n}: {_describe_range(r)}" for n, r in REFERENCE_RANGES.items()
        if any(n in rec["markers"] for rec in records)
    ))


def _describe_range(r):
    if "low" in r:
        return f"min {_format_value_min(r,'low')}"
    if "high" in r:
        return f"max {_format_value_min(r,'high')}"
    if "good_min" in r and "good_max" in r:
        return f"{_format_value_min(r,'good_min')}–{_format_value_min(r,'good_max')}"
    return "?"


def _format_value_min(r, key):
    v = r[key]
    return str(int(v)) if v == int(v) else str(round(v, 2))


def cmd_demo(args, records):
    """Seed a few believable sample records (your June and Oct 2026 panels)."""
    sample = [
        {"date": "2026-06-10", "note": "routine",
         "markers": {"ferritin": 12.4, "ggt": 86, "fib": 3.1, "mcv": 76.0,
                     "hemoglobin": 112.0, "carbamazepine": 7.2}},
        {"date": "2026-10-01", "note": "routine follow-up",
         "markers": {"ferritin": 22.0, "ggt": 90, "fib": 3.4, "mcv": 79.0,
                     "hemoglobin": 118.0, "carbamazepine": 6.5}},
    ]
    # merge: only add records whose (date) is not already present
    existing = {r["date"] for r in records}
    added = 0
    for rec in sample:
        if rec["date"] not in existing:
            records.append(rec)
            existing.add(rec["date"])
            added += 1
    records.sort(key=lambda r: r["date"])
    _save(args.filepath, records)
    print(f"seeded {added} demo record(s)")


def build_parser():
    p = argparse.ArgumentParser(
        prog="hematrack",
        description="Track personal blood-test (lab) markers and see trends.",
    )
    p.add_argument("--file", dest="filepath", default=DEFAULT_FILE,
                   help=f"data file (default: {DEFAULT_FILE})")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="record a new test result")
    a.add_argument("--date", help="test date YYYY-MM-DD (default: today)")
    a.add_argument("--marker", action="append", default=[], metavar="name=value",
                   help="a marker, e.g. --marker ferritin=12.4 (repeatable)")
    a.add_argument("--note", default="", help="optional note")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="show all records as a table")
    l.set_defaults(func=cmd_list)

    t = sub.add_parser("trends", help="latest value, delta, and range check per marker")
    t.set_defaults(func=cmd_trends)

    d = sub.add_parser("demo", help="seed sample data so you can try the tool")
    d.set_defaults(func=cmd_demo)
    return p


# Support `hematrack add --ferritin 12.4` shorthand by converting --X <v> to markers.
_SHORTHAND_MARKERS = {"ferritin", "ggt", "carbamazepine", "hemoglobin", "mcv", "fib"}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    # pre-process shorthand marker flags: `--ferritin 12.4` -> --marker ferritin=12.4
    out = []
    shorthand = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--") and arg[2:] in _SHORTHAND_MARKERS and i + 1 < len(argv):
            shorthand.append((arg[2:], float(argv[i + 1])))
            i += 2
            continue
        out.append(arg)
        i += 1
    parser = build_parser()
    args = parser.parse_args(out)
    args.shorthand = shorthand
    records = _load(args.filepath)
    args.func(args, records)


if __name__ == "__main__":
    main()
