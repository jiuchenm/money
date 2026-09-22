"""Collect private, versioned Tencent inputs. Never writes to the public site."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

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

def yahoo(symbol, start, end):
    p1=int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp())
    p2=int((dt.datetime.fromisoformat(end)+dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc).timestamp())
    encoded=urllib.parse.quote(symbol,safe='')
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits'
    payload=json.loads(fetch(url))
    if payload['chart'].get('error'): raise ValueError(str(payload['chart']['error']))
    return {'source_url':url,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'payload':payload}

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
                result=f.result(); (out/(key.replace('^','index-').replace('=','-')+'.json')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8'); print(key,'OK')
                succeeded.append(key)
            except Exception as e:
                errors.append({'source':key,'error':str(e)}); print(key,'FAILED',type(e).__name__)
                stale=out/(key.replace('^','index-').replace('=','-')+'.json')
                if stale.exists():
                    archive=out/'prior-attempts';archive.mkdir(exist_ok=True)
                    stale.replace(archive/(stale.stem+'-'+dt.datetime.now(dt.timezone.utc).strftime('%H%M%S%f')+'.json'))
    (out/'collection.json').write_text(json.dumps({'date':a.date,'start':a.start,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'succeeded':succeeded,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    if not {'0700.HK','eastmoney'}.issubset(succeeded): raise SystemExit('Core source unavailable in this attempt')

if __name__=='__main__': main()
