# hematrack

A tiny, zero-dependency command-line tool to track your personal blood-test
(lab) results and watch trends over time. Pure Python standard library — no
`pip install` needed.

## Why

Blood panels are only meaningful in *context* — this week's ferritin versus
last quarter's, and whether a value has drifted out of reference range. Keep a
running record with one command, and let `trends` tell you at a glance what
moved and whether anything is flagged.

## Install

```bash
# clone or download, then run directly — no install required
./hematrack.py --help

# optional: drop it on your PATH and use `hematrack` instead
install -m755 hematrack.py ~/.local/bin/hematrack
hematrack --help
```

Requires **Python 3.8+** (just the standard library).

## Quick start

```bash
# seed sample data so you can see it working
hematrack demo

# record a blood test (today by default, or pass --date YYYY-MM-DD)
hematrack add --date 2026-06-10 --ferritin 12.4 --ggt 86 --carbamazepine 7.2

# markers are free-form; you can repeat --marker name=value
hematrack add --date 2026-10-01 \
    --marker ferritin=22 --marker ggt=90 --marker mcv=79 --marker hemoglobin=118

# view the table and the trend report
hematrack list
hematrack trends
```

Output of `hematrack trends`:

```
Carbamazepine (therapeutic)      6.5   (▼ 0.7 vs 2026-06-10)  ✓ in range
Ferritin (iron stores)            22   (▲ 9.6 vs 2026-06-10)  ✓ in range
GGT (liver enzyme)                90   (▲ 4 vs 2026-06-10)  ⚠ above reference (max 60)
Haemoglobin                       118   (▲ 6 vs 2026-06-10)  ⚠ outside reference range [120–150]
```

## Reference ranges

Reference limits are baked in as **illustrative defaults** (likely close to a
Singapore lab panel) and shown in the `trends` report. **Adjust them to your
own lab's ranges** — edit the `REFERENCE_RANGES` dict at the top of
`hematrack.py`. Any marker without a defined range is simply reported without a
range-check; no marker is ever "wrong," just un-flagged.

> ⚠ This tool is for tracking and spotting trends — **not medical advice**.
> Always discuss results with your clinician, especially anything flagged.

## Data

Records are stored as a JSON file. Default location:
`~/.hematrack/records.json`. Point at a different file with `--file`:

```bash
hematrack --file mydata.json demo
hematrack --file mydata.json trends
```

The file is human-readable and easy to back up or export elsewhere.

## Commands

| Command | Description |
|---|---|
| `add --date D --marker n=v [...]` | Record a test result (repeat `--marker`) |
| `add --ferritin 12.4` | Shorthand for common markers |
| `list` | Show all records as a table |
| `trends` | Latest value, delta vs previous, and range check per marker |
| `demo` | Seed sample data |

## Development

```bash
# run the (stdlib unittest) test suite
python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
