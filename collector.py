import time, urllib.error, copy, subprocess
from unittest.mock import patch
import datetime as dt, json, math, sqlite3, tempfile, unittest, urllib.request
from zoneinfo import ZoneInfo
def require(ok,msg):
    if not ok: raise ValueError(msg)
def num(x): return type(x) in (float,int) and math.isfinite(x)
def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=12) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (408,429,500,502,503,504) or attempt==2: raise
        except urllib.error.URLError as e:
            if not isinstance(e.reason,(TimeoutError,ConnectionError)) or attempt==2: raise
        except (TimeoutError,ConnectionError):
            if attempt==2: raise
        print("RETRY",url,attempt+1,flush=True)
        time.sleep(2**attempt)
def weather_fetch(url):
    try:
        return get(url)
    except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
        if isinstance(e,urllib.error.HTTPError) or (isinstance(e,urllib.error.URLError) and not isinstance(e.reason,(TimeoutError,ConnectionError))): raise
        print('WEATHER_TRANSPORT_FALLBACK',repr(e),flush=True)
        result=subprocess.run(['curl','--fail','--silent','--show-error','--ipv4','--connect-timeout','8','--max-time','18',url],capture_output=True,check=True,timeout=20)
        return json.loads(result.stdout)
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
    require(len(set(a['time']))==len(a['time']),'duplicate days')
    require(all(len(a[k])==len(a['time']) for k in ('temperature_2m_min','temperature_2m_max')),'daily length')
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
    def test_weather(self):
        day=dt.date(2026,1,1)
        keys={'temperature_2m':'°C','apparent_temperature':'°C','precipitation_probability':'%','wind_speed_10m':'km/h'}
        times=[f'{day}T{h:02}:00' for h in (8,9,17,18)]
        d=dict(timezone='Asia/Jerusalem',hourly_units=keys,hourly=dict(time=times,**{k:[10]*4 for k in keys}),daily_units={'temperature_2m_min':'°C','temperature_2m_max':'°C'},daily=dict(time=[str(day),str(day+dt.timedelta(days=1))],temperature_2m_min=[5,6],temperature_2m_max=[15,16]))
        self.assertEqual(len(weather(d,day,'fixture')),20)
        for group,key,value in [('hourly_units','temperature_2m','°F'),('hourly','precipitation_probability',[101]*4),('hourly','wind_speed_10m',[-1]*4),('hourly','temperature_2m',[True]*4),('hourly','time',times[:3]+[times[0]]),('daily','temperature_2m_min',[20,6]),('daily','time',[str(day)]*2),('daily','temperature_2m_max',[15]),('daily_units','temperature_2m_min','°F')]:
            with self.subTest(group=group,key=key):
                bad=copy.deepcopy(d); bad[group][key]=value
                with self.assertRaises(ValueError): weather(bad,day,'fixture')
    def test_retry(self):
        with patch('urllib.request.urlopen',side_effect=[urllib.error.URLError(TimeoutError()),TimeoutError(),TimeoutError()]) as f, patch('time.sleep'):
            with self.assertRaises(TimeoutError): get('https://example.com')
            self.assertEqual(f.call_count,3)
        with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://example.com',400,'bad',None,None)) as f:
            with self.assertRaises(urllib.error.HTTPError): get('https://example.com')
            self.assertEqual(f.call_count,1)
    def test_transport_fallback(self):
        with patch('__main__.get',side_effect=urllib.error.URLError(TimeoutError())), patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,b'{"ok":true}',b'')) as f:
            self.assertEqual(weather_fetch('https://example.com'),{'ok':True})
            self.assertIn('--ipv4',f.call_args.args[0])
            self.assertNotIn('--insecure',f.call_args.args[0])
        with patch('__main__.get',side_effect=ValueError('bad data')), patch('subprocess.run') as f:
            with self.assertRaises(ValueError): weather_fetch('https://example.com')
            f.assert_not_called()
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
    tasks=[('weather',lambda:weather(weather_fetch(url),day,url))]
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
    from market_history import MarketTests
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Tests),
                              unittest.defaultTestLoader.loadTestsFromTestCase(MarketTests)])
    require(unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(),'regressions')
    live()
