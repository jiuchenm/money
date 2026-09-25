"""Provider selection with field-level provenance; never synthesize turnover."""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path
import pandas as pd

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def eastmoney_frame(raw):
    data=raw.get('payload',{}).get('data')
    if not data or data.get('code')!='00700' or not data.get('klines'):
        raise ValueError('Invalid Eastmoney Tencent response')
    cols=['date','open','close','high','low','volume','turnover','amplitude','change_pct','change','turnover_rate']
    result=pd.DataFrame([r.split(',') for r in data['klines']],columns=cols).set_index('date').astype(float)
    result.index=pd.to_datetime(result.index)
    return validate_rows(result)

def validate_rows(frame):
    if frame.empty or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Empty, duplicate or unsorted daily observations')
    values=frame[['open','high','low','close','volume']]
    if values.isna().any().any() or not values.map(math.isfinite).all().all():
        raise ValueError('Non-finite daily OHLCV')
    if (frame.volume<0).any() or (frame[['open','high','low','close']]<=0).any().any():
        raise ValueError('Invalid daily price or volume')
    if ((frame.high<frame[['open','close','low']].max(axis=1)-.011)|
        (frame.low>frame[['open','close']].min(axis=1)+.011)).any():
        raise ValueError('Invalid daily price range')
    return frame

def tencent_frame(raw):
    data=raw.get('data',{}).get('hk00700',{})
    # Do not silently substitute qfqday: only unadjusted day is comparable.
    rows=data.get('day')
    if not rows:raise ValueError('Tencent unadjusted day array missing')
    result=pd.DataFrame([r[:6] for r in rows],columns=['date','open','close','high','low','volume']).set_index('date').astype(float)
    result.index=pd.to_datetime(result.index)
    result['turnover']=float('nan');result['turnover_rate']=float('nan')
    return validate_rows(result)

def quote_turnover(raw,asof,row):
    q=raw.get('data',{}).get('hk00700',{}).get('qt',{}).get('hk00700',[])
    if len(q)<76 or q[2]!='00700' or q[75]!='HKD':return None
    try:
        stamp=dt.datetime.strptime(q[30],'%Y/%m/%d %H:%M:%S')
        if stamp.date().isoformat()!=asof or stamp.time()<dt.time(16,8):return None
        volume=float(q[6]);amount=float(q[37])
        if volume<=0 or not math.isfinite(amount) or amount<=0:return None
        if abs(float(q[3])-row['close'])>.011 or abs(volume-row['volume'])>1:return None
        # Amount is reported by the provider, not calculated from close * volume.
        if not row['low']-.011<=amount/volume<=row['high']+.011:return None
        return {'amount':amount,'turnover_rate':float(q[59]),'quote_time':stamp.isoformat(),
            'field':'qt.hk00700[37]','currency':'HKD'}
    except (TypeError,ValueError,IndexError):return None

def cached_amounts(frame,asof,history_root):
    used=[]
    for path in sorted(history_root.glob('tencent-????-??-??/raw/eastmoney.json'),reverse=True):
        snapshot_date=path.parents[1].name.removeprefix('tencent-')
        if snapshot_date>=asof:continue
        try:
            raw=read(path);old=eastmoney_frame(raw)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):continue
        n=0
        for date in frame.index.intersection(old.index):
            # Only fill same-date historical amounts, after quote/volume agreement.
            if date>=pd.Timestamp(asof) or pd.notna(frame.loc[date,'turnover']):continue
            if any(abs(frame.loc[date,k]-old.loc[date,k])>.011 for k in ['open','high','low','close']):continue
            if abs(frame.loc[date,'volume']-old.loc[date,'volume'])>1:continue
            if not math.isfinite(old.loc[date,'turnover']) or old.loc[date,'turnover']<=0:continue
            frame.loc[date,['turnover','turnover_rate']]=old.loc[date,['turnover','turnover_rate']]
            n+=1
        if n:used.append({'snapshot_date':snapshot_date,'fetched_at':raw.get('fetched_at'),'rows':n})
        if frame.loc[frame.index<pd.Timestamp(asof),'turnover'].notna().all():break
    return used

def select_daily(raw_dir,asof,history_root=None):
    manifest=read(raw_dir/'collection.json')
    failures={e['source'] for e in manifest.get('errors',[])}
    reasons=[]
    em_path=raw_dir/'eastmoney.json'
    if em_path.exists() and 'eastmoney' not in failures:
        try:
            raw=read(em_path);frame=eastmoney_frame(raw).loc['2023-01-05':asof].copy()
            if frame.index[-1].date().isoformat()!=asof:raise ValueError('Eastmoney latest day is stale')
            return frame,{'provider':'eastmoney','source_file':'eastmoney.json','fetched_at':raw['fetched_at'],
                'source_url':raw['source_url'],'fallback_used':False,'missing_turnover_dates':[],
                'turnover_sources':[{'source':'Eastmoney','rows':len(frame)}]}
        except (ValueError,KeyError,TypeError) as error:reasons.append(str(error))
    else:reasons.append('Eastmoney request failed or file absent')
    tx_path=raw_dir/'tencent-crosscheck.json'
    if not tx_path.exists() or 'tencent-crosscheck' in failures:
        raise ValueError('No current primary daily source: Eastmoney and Tencent unavailable')
    raw=read(tx_path);frame=tencent_frame(raw).loc['2023-01-05':asof].copy()
    if frame.index[-1].date().isoformat()!=asof:raise ValueError('Stale core data: Tencent fallback latest day is stale')
    caches=cached_amounts(frame,asof,history_root or raw_dir.parents[1])
    quote=quote_turnover(raw,asof,frame.iloc[-1])
    if quote:
        frame.loc[frame.index[-1],'turnover']=quote['amount']
        frame.loc[frame.index[-1],'turnover_rate']=quote['turnover_rate']
    return frame,{'provider':'tencent','source_file':'tencent-crosscheck.json','fetched_at':raw['_fetched_at'],
        'source_url':raw['_source_url'],'fallback_used':True,'fallback_reason':reasons,
        'turnover_sources':caches,'latest_turnover_quote':quote,
        'missing_turnover_dates':[d.date().isoformat() for d in frame.index[frame.turnover.isna()]],
        'note':'Tencent未复权OHLCV与Yahoo交叉核验；历史成交额只复用同日同价同量记录，当前成交额只取同日收盘报价；缺失保持空值。'}
