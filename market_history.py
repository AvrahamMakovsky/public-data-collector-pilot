"""Market History v0.2: personal-use FRED CSV reader, synthetic public CI.
No licensed observations are bundled. TASE/FTSE remain gated.
"""
import argparse
import csv
import datetime as dt
import io
import json
import math
import os
import unittest
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

FRED = {"SP500": "S&P 500", "NASDAQ100": "Nasdaq 100"}
GATED = ("FTSE All-World", "TA-35", "TA-125", "1183441", "1209220", "1186063")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def fred_url(series, as_of):
    require(series in FRED, "unknown series")
    return "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urlencode(
        {"id": series, "cosd": as_of - dt.timedelta(days=380), "coed": as_of}
    )


def parse_fred(text, series, as_of):
    require(series in FRED, "unknown series")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    require(reader.fieldnames in (["observation_date", series], ["DATE", series]),
            "wrong CSV identity/schema")
    key = reader.fieldnames[0]
    seen, rows = set(), {}
    for row in reader:
        require(set(row) == {key, series} and None not in row.values(), "malformed row")
        day = dt.date.fromisoformat(row[key])
        require(day <= as_of and day not in seen, "future/duplicate date")
        seen.add(day)
        value = row[series].strip()
        if value in ("", "."):
            continue
        price = float(value)
        require(math.isfinite(price) and price > 0, "invalid index level")
        rows[day] = price
    require(bool(rows), "no observations")
    return rows


def market_history(rows, series, as_of, source, input_kind):
    require(series in FRED, "unknown series")
    require(bool(rows), "no observations")
    require(all(type(d) is dt.date and d <= as_of and type(v) in (int, float)
                and math.isfinite(v) and v > 0 for d, v in rows.items()), "invalid observations")
    dates = sorted(rows)
    end = dates[-1]
    require(0 <= (as_of - end).days <= 4, "stale latest close")
    require(len(dates) >= 2, "missing previous close")
    require(all(d.weekday() < 5 for d in dates), "unexpected US weekend observation")
    window = end - dt.timedelta(days=363)
    target = end - dt.timedelta(days=365)
    candidates = [d for d in dates if 0 <= (target - d).days <= 7]
    require(bool(candidates), "missing annual baseline")
    annual = candidates[-1]
    checked = [d for d in dates if d >= annual]
    require(all((b-a).days <= 7 for a,b in zip(checked,checked[1:])), "history gap")
    def baseline(days):
        target = end - dt.timedelta(days=days)
        eligible = [d for d in dates if 0 <= (target-d).days <= 7]
        require(bool(eligible), "missing baseline")
        return eligible[-1]
    def field(value, unit, day):
        return {"value": value, "unit": unit, "date": str(day), "source": source}
    def change(day):
        require(day < end, "invalid baseline")
        value = 100 * (rows[end] / rows[day] - 1)
        require(math.isfinite(value), "non-finite return")
        return dict(field(value, "%", end), baseline_date=str(day), baseline=rows[day],
                    verification_status="PROVISIONAL_CALENDAR_UNVERIFIED",
                    elapsed_calendar_days=(end-day).days)
    series_dates = [d for d in dates if d >= window]
    require(series_dates and (series_dates[0]-window).days <= 7, "incomplete 52-week window")
    lo = min(series_dates, key=rows.get)
    hi = max(series_dates, key=rows.get)
    missing_weekdays = [str(annual+dt.timedelta(days=i))
                        for i in range((end-annual).days+1)
                        if (annual+dt.timedelta(days=i)).weekday()<5
                        and annual+dt.timedelta(days=i) not in rows]
    daily = dict(change(dates[-2]), basis="previous available observation; not verified previous trading session")
    return {
        "verification_status": "PROVISIONAL_CALENDAR_UNVERIFIED",
        "unexplained_weekdays_including_possible_holidays": missing_weekdays,
        "instrument": series, "variant": "price index, daily close",
        "input_kind": input_kind, "calendar_validation": "bounded gaps; exchange holiday calendar not verified",
        "level": field(rows[end], "index points", end),
        "1D": daily, "1W": dict(change(baseline(7)), basis="7 calendar days, prior available observation"),
        "1Y": dict(change(annual), basis="365 calendar days, prior available observation"),
        "52W_low_close": dict(field(rows[lo], "index points", lo), verification_status="PROVISIONAL_CALENDAR_UNVERIFIED"),
        "52W_high_close": dict(field(rows[hi], "index points", hi), verification_status="PROVISIONAL_CALENDAR_UNVERIFIED"),
        "series": [field(rows[d], "index points", d) for d in series_dates],
    }


def private_fetch(series, as_of):
    # Prevent accidental data redistribution in CI. Use only for personal use.
    require(not os.getenv("CI") and not os.getenv("GITHUB_ACTIONS"), "live market retrieval disabled in CI")
    url = fred_url(series, as_of)
    with urlopen(url, timeout=15) as response:
        final = urlsplit(response.geturl())
        require(final.scheme == "https" and final.hostname == "fred.stlouisfed.org",
                "unexpected provider redirect")
        raw = response.read(2_000_001)
    require(len(raw) <= 2_000_000, "response too large")
    return market_history(parse_fred(raw.decode("utf-8-sig"), series, as_of),
                          series, as_of, url, "live FRED CSV")


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.end = dt.date(2026, 1, 5)
        self.rows = {self.end-dt.timedelta(days=n): 100.0+n/100
                     for n in range(380) if (self.end-dt.timedelta(days=n)).weekday()<5}
    def calc(self, rows=None):
        return market_history(self.rows if rows is None else rows, "SP500", self.end,
                              "synthetic fixture", "synthetic")
    def test_returns_and_range(self):
        x = self.calc()
        self.assertEqual(x["level"]["value"], 100)
        self.assertEqual(x["1D"]["baseline_date"], "2026-01-02")
        self.assertAlmostEqual(x["1W"]["value"], 100*(100/100.07-1))
        self.assertEqual(x["1Y"]["baseline_date"], "2025-01-03")
        self.assertAlmostEqual(x["1Y"]["value"], 100*(100/103.67-1))
        self.assertEqual(x["52W_low_close"]["value"], 100)
        self.assertTrue(all(r["source"]=="synthetic fixture" for r in x["series"]))
    def test_csv_identity_missing_and_duplicates(self):
        good = "observation_date,SP500\n2026-01-02,100\n2026-01-03,.\n"
        self.assertEqual(parse_fred(good,"SP500",self.end),{dt.date(2026,1,2):100})
        for bad in (good.replace("SP500","NASDAQ100"), good+"2026-01-02,101\n",
                    good+"2026-01-06,.\n",good.replace(",100",",NaN"),
                    good.replace(",100",",-1"),good.replace(",100",",100,extra")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_fred(bad,"SP500",self.end)
    def test_missing_stale_gap_and_numeric(self):
        for bad in (
            {d:v for d,v in self.rows.items() if (self.end-d).days<200},
            {d:v for d,v in self.rows.items() if (self.end-d).days>5},
            {d:v for d,v in self.rows.items() if not 50<=(self.end-d).days<=65},
            dict(self.rows, **{}) | {self.end: True},
            self.rows | {self.end+dt.timedelta(days=1):100},
        ):
            with self.subTest(count=len(bad)):
                with self.assertRaises(ValueError):
                    self.calc(bad)
    def test_live_ci_gate(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"GITHUB_ACTIONS":"true"}), patch(__name__+".urlopen") as fetch:
            with self.assertRaises(ValueError):
                private_fetch("SP500",self.end)
            fetch.assert_not_called()
    def test_missing_session_not_verified(self):
        rows = dict(self.rows)
        del rows[dt.date(2026,1,2)]
        result = self.calc(rows)
        self.assertEqual(result["1D"]["verification_status"], "PROVISIONAL_CALENDAR_UNVERIFIED")
        self.assertIn("2026-01-02", result["unexplained_weekdays_including_possible_holidays"])
        self.assertEqual(result["1D"]["baseline_date"], "2026-01-01")
        with self.assertRaises(ValueError):
            self.calc(self.rows | {dt.date(2026,1,3):100})
    def test_no_substitution(self):
        with self.assertRaises(ValueError):
            fred_url("FTSE All-World",self.end)
        self.assertEqual(len(GATED),6)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("series",choices=FRED)
    p.add_argument("--as-of",required=True,type=dt.date.fromisoformat)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--csv",help="official FRED CSV downloaded for personal use")
    mode.add_argument("--fetch",action="store_true",help="personal-use live retrieval")
    p.add_argument("--personal-use",action="store_true",required=True)
    a = p.parse_args()
    require(not os.getenv("CI") and not os.getenv("GITHUB_ACTIONS"), "real market output disabled in CI")
    if a.fetch:
        result = private_fetch(a.series,a.as_of)
    else:
        with open(a.csv,encoding="utf-8-sig") as f:
            data=f.read(2_000_001)
        require(len(data)<=2_000_000,"input too large")
        result=market_history(parse_fred(data,a.series,a.as_of),a.series,a.as_of,
                              "https://fred.stlouisfed.org/series/"+a.series,
                              "user-supplied CSV; origin not independently authenticated")
    print(json.dumps(result,allow_nan=False,sort_keys=True))


if __name__ == "__main__":
    main()
