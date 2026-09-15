import json, threading, time, urllib.parse, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_lock=threading.Lock()
_cache={"status":"LOADING","error":None,"area":"SE2","currency":"SEK","resolution_minutes":60,"updated":None,"prices":[],"plan":[]}

def _fetch_day(day):
    q=urllib.parse.urlencode({"currency":"SEK","market":"DayAhead","date":day.strftime("%Y-%m-%d"),"resolutionInMinutes":60,"indexNames":"SE2"})
    url="https://dataportal-api.nordpoolgroup.com/api/DayAheadPriceIndices?"+q
    req=urllib.request.Request(url,headers={"User-Agent":"EnergyAI/0.16","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def _extract(payload):
    rows=[]
    items=payload if isinstance(payload,list) else payload.get("data",payload.get("rows",payload.get("priceIndices",[]))) if isinstance(payload,dict) else []
    if isinstance(items,dict): items=[items]
    def walk(x):
        if isinstance(x,dict):
            name=str(x.get("indexName",x.get("name",x.get("deliveryArea",""))))
            prices=x.get("prices")
            if (name=="SE2" or not name) and isinstance(prices,list):
                for p in prices:
                    if isinstance(p,dict):
                        st=p.get("deliveryStart",p.get("startTime",p.get("start")))
                        val=p.get("price",p.get("value"))
                        if st is not None and val is not None:
                            try: rows.append({"start":st,"sek_per_mwh":float(val),"ore_per_kwh":round(float(val)/10.0,3)})
                            except: pass
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(items)
    uniq={r["start"]:r for r in rows}
    return sorted(uniq.values(),key=lambda r:r["start"])

def _plan(prices):
    if not prices:return []
    vals=[p["ore_per_kwh"] for p in prices]
    lo=sorted(vals)[max(0,len(vals)//4-1)]; hi=sorted(vals)[min(len(vals)-1,(len(vals)*3)//4)]
    out=[]
    for p in prices:
        a="LADDA" if p["ore_per_kwh"]<=lo else "ANVÄND BATTERI" if p["ore_per_kwh"]>=hi else "VÄNTA"
        out.append({**p,"action":a})
    return out

def refresh():
    stockholm=ZoneInfo("Europe/Stockholm"); now=datetime.now(stockholm)
    try:
        rows=[]
        for d in (now.date(),(now+timedelta(days=1)).date()):
            try: rows+=_extract(_fetch_day(d))
            except Exception:
                if d==now.date(): raise
        # Keep upcoming 24 hourly index points.
        upcoming=[]
        for r in rows:
            try:
                dt=datetime.fromisoformat(str(r["start"]).replace("Z","+00:00")).astimezone(stockholm)
                if dt>=now-timedelta(hours=1): upcoming.append({**r,"local":dt.isoformat()})
            except: pass
        upcoming=upcoming[:24]
        with _lock:_cache.update({"status":"LIVE","error":None,"updated":datetime.now().isoformat(),"prices":upcoming,"plan":_plan(upcoming)})
    except Exception as e:
        with _lock:_cache.update({"status":"ERROR","error":f"{type(e).__name__}: {e}","updated":datetime.now().isoformat()})

def loop():
    while True:
        refresh();time.sleep(900)

def start():
    threading.Thread(target=loop,daemon=True,name="nordpool-prices").start()

def snapshot():
    with _lock:return dict(_cache)
