# Market History v0.2 — bounded pilot

Baseline 95fc798bdad60bd8e507e295bdd9af313e8d492f. The existing workflow runs original weather/FX and new synthetic market tests. No workflow configuration change.

FRED SP500 / NASDAQ100 are copyrighted price indices: personal-use retrieval only, never publish raw observations or histories to public CI. Source terms: https://fred.stlouisfed.org/legal/ and series notes. Run locally outside CI:
`python3 market_history.py SP500 --as-of YYYY-MM-DD --csv downloaded.csv --personal-use`
or use `--fetch` instead of `--csv` for a personal-use direct CSV attempt. Live connectivity not yet verified. CSV provenance is user-supplied, not authenticated. Previous close, calendar-week/365-day baselines, 52-week range of daily closes; bounded gap checks do not prove exchange calendar completeness.

TASE TA-35/TA-125 and securities 1183441/1209220/1186063: free official browser exports documented; machine schema, units and data-use permission unresolved. FTSE All-World exact series access unresolved. No proxy substitution. These six instruments remain unavailable pending lawful provider verification; no public dataset upload. Existing temporary SQLite checkpoint is not cross-run persistence.

## Independent review hardening
All market returns and ranges are provisional until an authoritative trading-session calendar is checked. Missing weekdays (including possible holidays) are exposed. The 1D key means previous available observation, not an independently verified previous trading session. 52-week window includes 364 calendar dates. Direct download connectivity and permission for automated FRED retrieval remain unverified; use official personal-use manual downloads until confirmed.

TASE source inventory (public instrument metadata, not historical observations): TA-35 index 142; TA-125 index 137 (GTR, not US-style price index); ETF 1183441 IE00B3YCGJ38, 1209220 IE000716YHJ7, 1186063 IE00BNRQM384. Official table headers include Date / Closing Index Price and Date / Closing Price (0.01 ILS) / Adjusted Closing Price. Actual export files have not been retrieved, so no production parser or automated endpoint is claimed. Keep the original adjusted/unadjusted distinction and exact security identification. Official FAQ https://www.tase.co.il/en/support-page?questionCode=Inv303 ; data licensing https://www.tase.co.il/en/content/products_lobby/data_services .
