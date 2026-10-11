import json
import os
import sys
import tempfile
import unittest

# make the project root importable regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hematrack  # noqa: E402


def run(argv, filepath=None):
    """Invoke the CLI's main() and return (rc, out, err, path)."""
    import io
    from contextlib import redirect_stdout, redirect_stderr

    if filepath is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()
        os.unlink(tmp.name)
        filepath = tmp.name
    full = ["--file", filepath] + argv
    out, err = io.StringIO(), io.StringIO()
    rc = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            hematrack.main(full)
    except SystemExit as e:
        rc = e.code or 0
    return rc, out.getvalue(), err.getvalue(), filepath


class TestRangeJudgement(unittest.TestCase):
    def test_ferritin_low(self):
        self.assertEqual(hematrack._range_judgement("ferritin", 10.0)[0], "FLAG")
        self.assertEqual(hematrack._range_judgement("ferritin", 30.0)[0], "OK")

    def test_ggt_high(self):
        self.assertEqual(hematrack._range_judgement("ggt", 70)[0], "FLAG")
        self.assertEqual(hematrack._range_judgement("ggt", 45)[0], "OK")

    def test_carbamazepine_window(self):
        self.assertEqual(hematrack._range_judgement("carbamazepine", 2)[0], "FLAG")
        self.assertEqual(hematrack._range_judgement("carbamazepine", 6.5)[0], "OK")
        self.assertEqual(hematrack._range_judgement("carbamazepine", 14)[0], "FLAG")

    def test_unregistered_marker_no_flags(self):
        self.assertEqual(hematrack._range_judgement("cholestrol", 5.2), (None, None))


class TestParse(unittest.TestCase):
    def test_good_date(self):
        self.assertEqual(hematrack._parse_date("2026-10-01").isoformat(), "2026-10-01")

    def test_parse_marker(self):
        self.assertEqual(hematrack._parse_marker("ferritin=12.4"), ("ferritin", 12.4))
        self.assertEqual(hematrack._parse_marker("GGT=86"), ("ggt", 86.0))


class TestCLI(unittest.TestCase):
    def test_add_and_list_and_trends(self):
        rc, out, _, fn = run(["add", "--date", "2026-06-10", "--ferritin", "12.4", "--ggt", "86"])
        self.assertEqual(rc, 0, f"add failed: {out}")
        with open(fn) as fh:
            data = json.load(fh)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["markers"]["ferritin"], 12.4)

        rc, out, _, fn = run(["add", "--date", "2026-10-01", "--ferritin", "22", "--ggt", "90"], fn)
        with open(fn) as fh:
            data = json.load(fh)
        self.assertEqual([r["date"] for r in data], ["2026-06-10", "2026-10-01"])

        rc, out, err, _ = run(["trends"], fn)
        self.assertEqual(rc, 0, err)
        self.assertIn("GGT", out)
        self.assertIn("above reference", out)

    def test_demo_seeds(self):
        rc, out, _, fn = run(["demo"])
        self.assertEqual(rc, 0)
        with open(fn) as fh:
            data = json.load(fh)
        self.assertEqual(len(data), 2)

    def test_bad_date_exits(self):
        rc, out, err, _ = run(["add", "--date", "not-a-date", "--ferritin", "1"])
        self.assertNotEqual(rc, 0)
        self.assertIn("bad date", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
