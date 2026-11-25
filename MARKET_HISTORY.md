# Market History v0.2 — bounded pilot

Baseline 95fc798bdad60bd8e507e295bdd9af313e8d492f. The existing workflow runs original weather/FX and new synthetic market tests. No workflow configuration change.

FRED SP500 / NASDAQ100 are copyrighted price indices: personal-use retrieval only, never publish raw observations or histories to public CI. Source terms: https://fred.stlouisfed.org/legal/ and series notes. Run locally outside CI:
`python3 market_history.py SP500 --as-of YYYY-MM-DD --csv downloaded.csv --personal-use`
or use `--fetch` instead of `--csv` for a personal-use direct CSV attempt. Live connectivity not yet verified. CSV provenance is user-supplied, not authenticated. Previous close, calendar-week/365-day baselines, 52-week range of daily closes; bounded gap checks do not prove exchange calendar completeness.

TASE TA-35/TA-125 and securities 1183441/1209220/1186063: free official browser exports documented; machine schema, units and data-use permission unresolved. FTSE All-World exact series access unresolved. No proxy substitution. These six instruments remain unavailable pending lawful provider verification; no public dataset upload. Existing temporary SQLite checkpoint is not cross-run persistence.
