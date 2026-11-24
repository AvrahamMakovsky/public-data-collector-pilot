import datetime as dt, json, math, sqlite3, tempfile, unittest, urllib.request
from zoneinfo import ZoneInfo
def require(ok,msg):
    if not ok: raise ValueError(msg)
def num(x): return type(x) in (float,int) and math.isfinite(x)
def get(url):
    with urllib.request.urlopen(url,timeout=20) as r: return json.load(r)
def evidence(value,unit,date,url):
    return dict(value=value,unit=unit,date=str(date),source=url)
def fx(rows,b,q,day,url):
    rates={}
    for r in rows:
        d=dt.date.fromisoformat(r['date'])
        require(r['base']==b and r['quote']==q and d<=day and d not in rates,'identity/date')
        require(num(r['rate']) and r['rate']>0,'rate')
        rates[d]=r['rate']
    end=max(rates)
    require(0<=(day-end).days<=4,'stale')
    out={'level':evidence(rates[end],q+'/'+b,end,url)}
    for label,n in [('1D',1),('1W',7),('1M',30),('1Y',365)]:
        target=end-dt.timedelta(days=n)
        candidates=[d for d in rates if 0<=(target-d).days<=4]
        require(bool(candidates),'missing '+label)
        d=max(candidates)
        out[label]=dict(evidence(100*(rates[end]/rates[d]-1),'%',end,url),baseline_date=str(d),baseline=rates[d])
    return out
def weather(d,day,url):
    require(d['timezone']=='Asia/Jerusalem','timezone')
    out={}
    units={'temperature_2m':'°C','apparent_temperature':'°C','precipitation_probability':'%','wind_speed_10m':'km/h'}
    h=d['hourly']; require(len(set(h['time']))==len(h['time']),'duplicate hours')
    for hour in (8,9,17,18):
        stamp=f'{day}T{hour:02}:00'; i=h['time'].index(stamp)
        for k,u in units.items():
            require(d['hourly_units'][k]==u and len(h[k])==len(h['time']),'hourly units/length')
            v=h[k][i]; require(num(v),'numeric')
            require(k!='precipitation_probability' or 0<=v<=100,'rain')
            require(k!='wind_speed_10m' or v>=0,'wind')
            out[f'{hour:02}/{k}']=evidence(v,u,stamp,url)
    a=d['daily']
    for offset in (0,1):
        date=str(day+dt.timedelta(days=offset)); i=a['time'].index(date)
        lo,hi=[a[k][i] for k in ('temperature_2m_min','temperature_2m_max')]
        require(all(d['daily_units'][k]=='°C' for k in ('temperature_2m_min','temperature_2m_max')),'daily units')
        require(num(lo) and num(hi) and lo<=hi,'daily range')
        for k,v in [('min',lo),('max',hi)]: out[f'{date}/{k}']=evidence(v,'°C',date,url)
    return out
class Ledger:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('create table if not exists checkpoints(run text, category text, payload text, primary key(run,category))')
    def collect(self,run,category,fn):
        row=self.db.execute('select payload from checkpoints where run=? and category=?',(run,category)).fetchone()
        if row: return json.loads(row[0])
        p=fn(); require(bool(p),'empty payload')
        s=json.dumps(p,allow_nan=False,sort_keys=True)
        with self.db: self.db.execute('insert into checkpoints values(?,?,?)',(run,category,s))
        return json.loads(s)
class Tests(unittest.TestCase):
    def test_fx(self):
        day=dt.date(2026,1,1)
        rows=[dict(date=str(day-dt.timedelta(days=n)),base='USD',quote='ILS',rate=2 if n else 3) for n in (0,1,7,30,365)]
        self.assertEqual(fx(rows,'USD','ILS',day,'fixture')['1Y']['value'],50)
        for bad in [rows[:-1],rows+[rows[0]], [dict(r,quote='EUR') for r in rows], [dict(r,rate=True) for r in rows]]:
            with self.assertRaises(ValueError): fx(bad,'USD','ILS',day,'fixture')
    def test_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            p=t+'/db'; a=Ledger(p)
            a.collect('r','a',lambda:{'ok':1})
            with self.assertRaises(ValueError): a.collect('r','b',lambda: {})
            a.db.close(); b=Ledger(p)
            self.assertEqual(b.collect('r','a',lambda: self.fail('recollected')),{'ok':1})
            self.assertEqual(b.collect('r','b',lambda:{'ok':2}),{'ok':2})
def live():
    day=dt.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
    url='https://api.open-meteo.com/v1/forecast?latitude=31.78&longitude=35.22&hourly=temperature_2m,apparent_temperature,precipitation_probability,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FJerusalem&forecast_days=2'
    tasks=[('weather',lambda:weather(get(url),day,url))]
    for b in ('USD','EUR'):
        for q in ('ILS','GEL'):
            def collect(b=b,q=q):
                u=f'https://api.frankfurter.dev/v2/rates?base={b}&quotes={q}&from={day-dt.timedelta(days=380)}&to={day}'
                return fx(get(u),b,q,day,u)
            tasks.append((b+q,collect))
    failures=[]
    with tempfile.TemporaryDirectory() as t:
        l=Ledger(t+'/db')
        for name,fn in tasks:
            try: print(name,'PASS',json.dumps(l.collect(str(day),name,fn),ensure_ascii=False),flush=True)
            except Exception as e: failures.append(name); print(name,'FAIL',repr(e),flush=True)
    require(not failures,str(failures))
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    require(unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(),'regressions')
    live()
