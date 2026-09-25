"""Collect private, versioned Tencent inputs. Never writes to the public site."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
import json
import hashlib
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
ASSETS = {
    '0700.HK': ('腾讯控股', 'HK'), '^HSI': ('恒生指数', 'HK'),
    '3033.HK': ('恒生科技ETF', 'HK'), 'QQQ': ('Nasdaq 100 ETF', 'US'),
    'SPY': ('S&P 500 ETF', 'US'), 'KWEB': ('中国互联网ETF', 'US'),
    'SOXX': ('半导体ETF', 'US'), '^VIX': ('VIX', 'US'),
    'DX-Y.NYB': ('美元指数', 'US'), 'CNH=X': ('USD/CNH', 'GLOBAL'),
    'HKD=X': ('USD/HKD', 'GLOBAL'), 'GC=F': ('黄金期货', 'GLOBAL'),
    'CL=F': ('WTI原油期货', 'GLOBAL'), 'HG=F': ('铜期货', 'GLOBAL'),
    'HYG': ('高收益债ETF', 'US'), 'LQD': ('投资级债ETF', 'US'),
    'TLT': ('长期美债ETF', 'US'),
}
FRED = {'DGS2':'美债2年收益率','DGS10':'美债10年收益率',
        'DFII10':'美债10年实际利率','BAMLH0A0HYM2':'高收益信用利差'}

def fetch(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 TencentPersonalResearch/1.0'})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode('utf-8')

def repair_yahoo_nulls(result,symbol,end,history_root=None):
    root=history_root or ROOT/'research-private'
    filename=symbol.replace('^','index-').replace('=','-')+'.json'
    series=result['payload']['chart']['result'][0]
    positions={v:i for i,v in enumerate(series.get('timestamp',[]))}
    repairs=[]
    candidates=list(root.glob('tencent-????-??-??/raw/'+filename))
    candidates+=list(root.glob('tencent-????-??-??/raw/prior-attempts/'+filename.removesuffix('.json')+'-*.json'))
    candidates+=list(root.glob('tencent-????-??-??/prior-failed-run/raw/'+filename))
    for path in sorted(candidates,reverse=True):
        folder=next((p.name for p in path.parents if p.name.startswith('tencent-20')),None)
        if folder is None or folder.removeprefix('tencent-')>end:continue
        try:
            cached=json.loads(path.read_text(encoding='utf-8'));old=cached['payload']['chart']['result'][0]
            if old['meta']['symbol']!=series['meta']['symbol']:continue
            oldq=old['indicators']['quote'][0];newq=series['indicators']['quote'][0]
            changed=[]
            for j,stamp in enumerate(old.get('timestamp',[])):
                if stamp not in positions or oldq['close'][j] is None:continue
                market=ASSETS.get(symbol,('', 'GLOBAL'))[1]
                local=dt.datetime.fromtimestamp(stamp,ZoneInfo(old['meta']['exchangeTimezoneName']))
                if market in ['HK','US']:
                    ready=local.replace(hour=18 if market=='US' else 16,minute=30,second=0)
                else:
                    ready=dt.datetime.combine(local.date()+dt.timedelta(days=1),dt.time(2),tzinfo=dt.timezone.utc)
                captured=dt.datetime.fromisoformat(cached['fetched_at'].replace('Z','+00:00'))
                if captured<ready:continue
                i=positions[stamp]
                fields=[]
                for key,values in newq.items():
                    if values[i] is None and key in oldq and oldq[key][j] is not None:
                        values[i]=oldq[key][j];fields.append(key)
                if fields:changed.append({'timestamp':stamp,'fields':fields})
            if changed:repairs.append({'snapshot_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'snapshot_fetched_at':cached['fetched_at'],'observations':changed})
        except (KeyError,TypeError,ValueError,IndexError):continue
    if repairs:result['same_timestamp_repairs']=repairs
    return result

def yahoo(symbol, start, end):
    p1=int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp())
    p2=int((dt.datetime.fromisoformat(end)+dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc).timestamp())
    encoded=urllib.parse.quote(symbol,safe='')
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits'
    payload=json.loads(fetch(url))
    if payload['chart'].get('error'): raise ValueError(str(payload['chart']['error']))
    result={'source_url':url,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'payload':payload}
    # Only fill nulls from the same observed timestamp, never carry forward another day.
    return repair_yahoo_nulls(result,symbol,end)

def eastmoney(start, end):
    query={'secid':'116.00700','fields1':'f1,f2,f3,f4,f5,f6',
           'fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
           'klt':'101','fqt':'0','beg':start.replace('-',''),'end':end.replace('-',''),'lmt':'1000000'}
    url='https://33.push2his.eastmoney.com/api/qt/stock/kline/get?'+urllib.parse.urlencode(query)
    return {'source_url':url,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'payload':json.loads(fetch(url))}

def tencent_crosscheck(end):
    url=f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=hk00700,day,2023-01-01,{end},1000,qfq'
    result=json.loads(fetch(url));result['_source_url']=url;result['_fetched_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument('--date',required=True); p.add_argument('--start',default='2016-01-01'); a=p.parse_args()
    out=ROOT/'research-private'/f'tencent-{a.date}'/'raw'; out.mkdir(parents=True,exist_ok=True)
    errors=[];succeeded=[]
    jobs={symbol:(lambda s=symbol:yahoo(s,a.start,a.date)) for symbol in ASSETS}
    jobs['eastmoney']=lambda:eastmoney(a.start,a.date)
    jobs['tencent-crosscheck']=lambda:tencent_crosscheck(a.date)
    def fred(series):
        url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
        return {'source_url':url,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'csv':fetch(url)}
    jobs.update({f'fred-{s}':(lambda s=s:fred(s)) for s in FRED})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fn):key for key,fn in jobs.items()}
        for f in concurrent.futures.as_completed(futures):
            key=futures[f]
            try:
                result=f.result()
                destination=out/(key.replace('^','index-').replace('=','-')+'.json')
                if destination.exists():
                    archive=out/'prior-attempts';archive.mkdir(exist_ok=True)
                    destination.replace(archive/(destination.stem+'-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.json'))
                destination.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8'); print(key,'OK')
                succeeded.append(key)
            except Exception as e:
                errors.append({'source':key,'error':str(e)}); print(key,'FAILED',type(e).__name__)
                stale=out/(key.replace('^','index-').replace('=','-')+'.json')
                if stale.exists():
                    archive=out/'prior-attempts';archive.mkdir(exist_ok=True)
                    stale.replace(archive/(stale.stem+'-'+dt.datetime.now(dt.timezone.utc).strftime('%H%M%S%f')+'.json'))
    (out/'collection.json').write_text(json.dumps({'date':a.date,'start':a.start,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'succeeded':succeeded,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    if '0700.HK' not in succeeded or not {'eastmoney','tencent-crosscheck'}.intersection(succeeded):
        raise SystemExit('Core price sources unavailable in this attempt')
    # Validate selected source and missing-field policy before declaring collection usable.
    from daily_sources import select_daily
    _,selection=select_daily(out,a.date)
    manifest=json.loads((out/'collection.json').read_text(encoding='utf-8'))
    manifest['daily_selection']=selection
    (out/'collection.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Daily source:',selection['provider'],'fallback:',selection['fallback_used'])

if __name__=='__main__': main()
