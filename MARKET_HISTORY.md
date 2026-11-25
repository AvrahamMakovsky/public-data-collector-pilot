# Market History v0.2 — bounded pilot

Baseline 95fc798bdad60bd8e507e295bdd9af313e8d492f. The existing workflow runs original weather/FX and new synthetic market tests. No workflow configuration change.

FRED SP500 / NASDAQ100 are copyrighted price indices: personal-use retrieval only, never publish raw observations or histories to public CI. Source terms: https://fred.stlouisfed.org/legal/ and series notes. Run locally outside CI:
`python3 market_history.py SP500 --as-of YYYY-MM-DD --csv downloaded.csv --personal-use`
or use `--fetch` instead of `--csv` for a personal-use direct CSV attempt. Live connectivity not yet verified. CSV provenance is user-supplied, not authenticated. Previous close, calendar-week/365-day baselines, 52-week range of daily closes; bounded gap checks do not prove exchange calendar completeness.

TASE TA-35/TA-125 and securities 1183441/1209220/1186063: free official browser exports documented; machine schema, units and data-use permission unresolved. FTSE All-World exact series access unresolved. No proxy substitution. These six instruments remain unavailable pending lawful provider verification; no public dataset upload. Existing temporary SQLite checkpoint is not cross-run persistence.

## Independent review hardening
All market returns and ranges are provisional until an authoritative trading-session calendar is checked. Missing weekdays (including possible holidays) are exposed. The 1D key means previous available observation, not an independently verified previous trading session. 52-week window includes 364 calendar dates. Direct download connectivity and permission for automated FRED retrieval remain unverified; use official personal-use manual downloads until confirmed.

TASE source inventory (public instrument metadata, not historical observations): TA-35 index 142; TA-125 index 137 (GTR, not US-style price index); ETF 1183441 IE00B3YCGJ38, 1209220 IE000716YHJ7, 1186063 IE00BNRQM384. Official table headers include Date / Closing Index Price and Date / Closing Price (0.01 ILS) / Adjusted Closing Price. Actual export files have not been retrieved, so no production parser or automated endpoint is claimed. Keep the original adjusted/unadjusted distinction and exact security identification. Official FAQ https://www.tase.co.il/en/support-page?questionCode=Inv303 ; data licensing https://www.tase.co.il/en/content/products_lobby/data_services .

## Published-session calendar v0.2.1
Snapshot reviewed 2026-11-25; bounded 2025-01-01 to 2026-12-31. Sources:
- NYSE: https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx
- Nasdaq: https://www.nasdaqtrader.com/trader.aspx?id=Calendar ; exceptional 2025-01-09 closure: https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2024-87
- TASE historical and current vacation tables: https://www.tase.co.il/en/content/knowledge_center/trading_vacation_schedule ; transition: https://www.tase.co.il/en/content/about/tradingdays_change/ ; pre-transition foreign funds: https://www.tase.co.il/en/content/knowledge_center/securities_derivatives

US and TASE schedule checks include early-close sessions as sessions. Israeli foreign ETFs: prior Mon-Thu, new Mon-Fri, plus Jan 1, Dec 25/26, Easter Monday exclusions; historical applicability of additional foreign-fund holidays should be confirmed before accepting real TASE returns. No automatic inference of exceptional closures. No dates extrapolated beyond range. TASE calendar is preparatory, not a live provider adapter. Election-day entry follows published vacation schedule, subject to actual exchange notices. Strict FRED CSV mode: add --require-schedule and set --as-of to a date through which sessions have completed. Strict status means matching the published schedule, not independent price authentication or emergency-closure verification. Outside covered dates or on missing sessions, reject. Existing provisional mode retained. No official export bytes obtained for TASE, so parser remains gated.

Personal-use source alternatives: official FRED graph CSV download https://fred.stlouisfed.org/help/data/downloading/using-the-download-data-link/ ; FRED API and official MCP connector https://fred.stlouisfed.org/help/data/connecting-fred-to-ai-services/fred-mcp-connector (separate accounts and terms). No registration, API key or licensed market observations in public CI. TASE FAQ https://www.tase.co.il/en/support-page?questionCode=Inv303 .
