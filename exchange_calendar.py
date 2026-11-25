"""Published exchange schedule snapshot, not a live exchange feed."""
import datetime as dt
import unittest

START, END = dt.date(2025,1,1), dt.date(2026,12,31)
TRANSITION=dt.date(2026,1,5)
VERSION="published-2025-2026-reviewed-2026-11-25"
def dates(s):
    return frozenset(dt.date.fromisoformat(d) for d in s.split())
US_CLOSED=dates("""
2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26
2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25
2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19
2026-07-03 2026-09-07 2026-11-26 2026-12-25
""")
IL_CLOSED=dates("""
2025-03-14 2025-04-13 2025-04-18 2025-04-30 2025-05-01 2025-06-01
2025-06-02 2025-08-03 2025-09-22 2025-09-23 2025-09-24 2025-10-01
2025-10-02 2025-10-06 2025-10-07 2025-10-13 2025-10-14
2026-01-04 2026-03-03 2026-04-01 2026-04-02 2026-04-07 2026-04-08
2026-04-21 2026-04-22 2026-05-21 2026-05-22 2026-07-23 2026-09-11
2026-09-13 2026-09-18 2026-09-20 2026-09-21 2026-09-25 2026-10-02
2026-10-27
""")
FOREIGN_EXTRA=dates("2025-01-01 2025-04-21 2025-12-25 2025-12-26 2026-01-01 2026-04-06 2026-12-25 2026-12-26")
MARKETS=("US","TASE","TASE_FOREIGN_ETF")
def scheduled_session(market,day):
    if market not in MARKETS or type(day) is not dt.date or not START<=day<=END:
        raise ValueError("calendar market/date outside reviewed scope")
    w=day.weekday()
    if market=="US":
        return w<5 and day not in US_CLOSED
    if day<TRANSITION:
        allowed=w in ((0,1,2,3) if market=="TASE_FOREIGN_ETF" else (6,0,1,2,3))
    else:
        allowed=w<5
    return allowed and day not in IL_CLOSED and (market!="TASE_FOREIGN_ETF" or day not in FOREIGN_EXTRA)

def scheduled_sessions(market,start,end):
    if market not in MARKETS or type(start) is not dt.date or type(end) is not dt.date or not START<=start<=end<=END:
        raise ValueError("calendar interval outside reviewed scope")
    days=(start+dt.timedelta(days=i) for i in range((end-start).days+1))
    return tuple(d for d in days if scheduled_session(market,d))

def check_coverage(market,observed,start,completed_through):
    expected=set(scheduled_sessions(market,start,completed_through))
    if not expected:
        raise ValueError("no scheduled sessions")
    observed=set(observed)
    actual={d for d in observed if start<=d<=completed_through}
    missing=sorted(expected-actual)
    unexpected=sorted(actual-expected)
    if any(d>completed_through for d in observed):
        raise ValueError("observation after cutoff")
    if missing or unexpected:
        raise ValueError("schedule mismatch missing="+",".join(map(str,missing))+
                         " unexpected="+",".join(map(str,unexpected)))
    return {"calendar_version":VERSION,"market":market,"start":str(start),
            "completed_through":str(completed_through),"expected_sessions":len(expected),
            "status":"MATCHED_PUBLISHED_SCHEDULE","latest_scheduled_session":str(max(expected)),
            "limitation":"caller-supplied cutoff; no independent emergency-closure or source authentication"}

class CalendarTests(unittest.TestCase):
    def test_us_exception_and_early_close(self):
        self.assertFalse(scheduled_session("US",dt.date(2025,1,9)))
        self.assertFalse(scheduled_session("US",dt.date(2026,11,26)))
        self.assertTrue(scheduled_session("US",dt.date(2026,11,27)))
    def test_tase_transition(self):
        for day,value in (("2025-12-28",True),("2026-01-04",False),("2026-01-05",True),("2026-01-09",True),("2026-01-11",False)):
            self.assertEqual(scheduled_session("TASE",dt.date.fromisoformat(day)),value)
    def test_tase_foreign_etf_distinction(self):
        for day,local,foreign in (("2025-12-28",True,False),("2026-01-01",True,False),("2026-04-06",True,False),("2026-04-03",True,True),("2026-09-18",False,False)):
            d=dt.date.fromisoformat(day)
            self.assertEqual(scheduled_session("TASE",d),local)
            self.assertEqual(scheduled_session("TASE_FOREIGN_ETF",d),foreign)
    def test_range_and_unknown_market_fail_closed(self):
        for market,start,end in (("US",dt.date(2024,12,31),START),("TASE",END,dt.date(2027,1,1)),("UNKNOWN",START,END),("US",END,START)):
            with self.assertRaises(ValueError):
                scheduled_sessions(market,start,end)
    def test_missing_latest_or_interior_and_unexpected(self):
        start,end=dt.date(2026,11,23),dt.date(2026,11,27)
        expected=set(scheduled_sessions("US",start,end))
        self.assertEqual(len(expected),4)
        self.assertEqual(check_coverage("US",expected,start,end)["expected_sessions"],4)
        for invalid in (expected-{end},expected-{dt.date(2026,11,24)},expected|{dt.date(2026,11,26)},expected|{end+dt.timedelta(days=1)}):
            with self.assertRaises(ValueError):
                check_coverage("US",invalid,start,end)
