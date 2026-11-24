import json, urllib.request, math
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
def get(url):
    with urllib.request.urlopen(url,timeout=15) as r:
        return json.load(r)
def positive(x):
    return type(x) in (int,float) and math.isfinite(x) and x>0
def weather():
    d=get("https://api.open-meteo.com/v1/forecast?latitude=31.78&longitude=35.22&hourly=temperature_2m,apparent_temperature,precipitation_probability,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FJerusalem&forecast_days=2")
    assert d["timezone"]=="Asia/Jerusalem"
    day=datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    for h in (8,9,17,18):
        i=d["hourly"]["time"].index(f"{day}T{h:02}:00")
        for k in ("temperature_2m","apparent_temperature","precipitation_probability","wind_speed_10m"):
            v=d["hourly"][k][i]
            assert type(v) in (int,float) and math.isfinite(v)
            if k=="precipitation_probability": assert 0<=v<=100
            if k=="wind_speed_10m": assert v>=0
    print("weather PASS",day,d["hourly_units"],flush=True)
def fx(base,quote):
    d=get(f"https://api.frankfurter.dev/v2/rates?base={base}&quotes={quote}")
    assert len(d)==1
    r=d[0]
    assert r["base"]==base and r["quote"]==quote and positive(r["rate"])
    age=(datetime.now(ZoneInfo("UTC")).date()-datetime.fromisoformat(r["date"]).date()).days
    assert 0<=age<=4
    print("FX PASS",r,flush=True)
if __name__=="__main__":
    failures=[]
    for name,fn in [("weather",weather)]+[(b+q,lambda b=b,q=q:fx(b,q)) for b in ("USD","EUR") for q in ("ILS","GEL")]:
        try: fn()
        except Exception as e:
            failures.append(name)
            print(name,"FAIL",repr(e),flush=True)
    if failures: raise SystemExit("Failed: "+",".join(failures))
