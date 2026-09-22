"""Point-in-time daily features and bounded, chronological model comparison.

Public output is intentionally a separate explicit step. Raw provider data stays private.
"""
from __future__ import annotations
import argparse
import datetime as dt
import io
import json
import math
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_pinball_loss
from collect import ROOT, ASSETS, FRED

HORIZONS = (5, 10, 20)
TARGETS = ('return', 'upside', 'downside', 'drawdown')
CALIBRATION = 126
TEST_BLOCK = 63
MAX_TRAIN = 1260
QUANTILES = (.1, .5, .9)
MARKET_CLOSURES = {
    '2023-09-01':'https://www.hkex.com.hk/News/Market-Communications/2023/2309012news?sc_lang=en',
    '2023-09-08':'https://www.hkex.com.hk/News/Market-Communications/2023/2309083news?sc_lang=en',
}

def load(path): return json.loads(path.read_text(encoding='utf-8'))

def clean(value):
    if isinstance(value, dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [clean(v) for v in value]
    if isinstance(value, np.generic): return clean(value.item())
    if isinstance(value, (pd.Timestamp,dt.datetime,dt.date)): return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value): return None
    return value

def save(path,value): path.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def yahoo_frame(path):
    raw=load(path); result=raw['payload']['chart']['result'][0]
    times=pd.to_datetime(result['timestamp'],unit='s',utc=True).tz_convert(result['meta']['exchangeTimezoneName'])
    q=result['indicators']['quote'][0]
    frame=pd.DataFrame(q,index=pd.DatetimeIndex(times.date)).sort_index()
    frame=frame.loc[~frame.index.duplicated(keep='last')].dropna(subset=['close'])
    return frame, result, raw

def dividend_amounts(index,events,timezone):
    amounts=pd.Series(0.,index=index)
    for event in events.get('dividends',{}).values():
        date=pd.Timestamp(event['date'],unit='s',tz='UTC').tz_convert(timezone).normalize().tz_localize(None)
        if date in amounts.index:amounts.loc[date]+=float(event['amount'])
    return amounts

def wealth_index(close,dividends):
    # Causal reinvested cash return: the dividend enters only on its ex-date.
    # Never uses today's back-adjusted price factor to reconstruct yesterday's state.
    gross=(close+dividends)/close.shift()
    if len(gross):gross.iloc[0]=1.
    return gross.cumprod()*100.

def normalize(raw_dir,asof):
    y,yr,_=yahoo_frame(raw_dir/'0700.HK.json')
    rows=[line.split(',') for line in load(raw_dir/'eastmoney.json')['payload']['data']['klines']]
    cols=['date','open','close','high','low','volume','turnover','amplitude','change_pct','change','turnover_rate']
    em=pd.DataFrame(rows,columns=cols).set_index('date').astype(float)
    em.index=pd.to_datetime(em.index)
    # Historical Yahoo OHLC before Tencent's 2023 in-specie distribution are on
    # a different adjustment basis. Do not treat thousands of adjustment differences
    # as independent price errors. First edition is bounded to the comparable era.
    frame=em.loc['2023-01-05':asof].copy()
    pair=y.join(em[['close','volume']],rsuffix='_em',how='inner').loc['2023-01-05':asof]
    diffs=pair[(pair.close-pair.close_em).abs()>.011]
    conflicts=[{'date':idx.date().isoformat(),'yahoo_close':row.close,'eastmoney_close':row.close_em} for idx,row in diffs.iterrows()]
    unmatched=sorted(set(frame.index)^set(y.loc['2023-01-05':asof].index))
    third_path=raw_dir/'tencent-crosscheck.json'
    third={r[0]:float(r[2]) for r in load(third_path)['data']['hk00700'].get('day',[])} if third_path.exists() else {}
    resolved=[]
    for event in conflicts:
        value=third.get(event['date'])
        event['third_source_close']=value
        event['resolution']='Eastmoney and Tencent match; vendor consensus, not exchange-certified' if value is not None and abs(value-event['eastmoney_close'])<.011 else 'unresolved'
        if event['resolution']!='unresolved': resolved.append(pd.Timestamp(event['date']))
    unresolved=diffs.index.difference(pd.DatetimeIndex(resolved))
    frame['conflict']=frame.index.isin(unresolved)|frame.index.isin(unmatched)
    frame['dividend_amount']=dividend_amounts(frame.index,yr.get('events',{}),'Asia/Hong_Kong')
    frame['dividend']=frame.dividend_amount>0
    # Explicitly exclude disputed price observations from rolling model features.
    for col in ['open','high','low','close']:
        frame[col]=frame[col].where(~frame['conflict'])
    cal=xcals.get_calendar('XHKG')
    expected=cal.sessions_in_range(pd.Timestamp(asof)-pd.Timedelta(days=10),pd.Timestamp(asof))
    expected=[s for s in expected if s.date().isoformat() not in MARKET_CLOSURES]
    if not expected or expected[-1].date().isoformat()!=asof:
        raise ValueError('Requested date is not a Hong Kong trading session; retain prior report')
    if not expected or frame.index[-1].date()!=expected[-1].date():
        raise ValueError(f'Stale core data: actual={frame.index[-1].date()}, expected={expected[-1].date() if expected else None}')
    if frame.iloc[-1]['conflict'] or frame.iloc[-1][['open','high','low','close','volume','turnover']].isna().any():
        raise ValueError('Latest core observation is unresolved or incomplete')
    expected_close=cal.session_close(expected[-1])
    if pd.Timestamp.now(tz='UTC')<expected_close:
        raise ValueError('Latest market session has not closed')
    collection=load(raw_dir/'collection.json')
    if collection.get('date')!=asof or any(e['source'] in ['0700.HK','eastmoney'] for e in collection.get('errors',[])):
        raise ValueError('Core sources failed or collection date mismatched')
    for source in ['0700.HK','eastmoney']:
        fetched=pd.Timestamp(load(raw_dir/(source+'.json'))['fetched_at'])
        if fetched<expected_close+pd.Timedelta(minutes=20):
            raise ValueError(f'{source} was not fetched after completed session plus buffer')
    sched=cal.schedule.loc[frame.index.min():frame.index.max()]
    sessions=set(sched.index.tz_localize(None) if sched.index.tz is not None else sched.index)
    unknown=[v.date().isoformat() for v in frame.index if v not in sessions]
    missing=sorted(v.date().isoformat() for v in sessions if v not in frame.index and v.date().isoformat() not in MARKET_CLOSURES)
    if missing or unknown: raise ValueError(f'Unresolved session mismatch: missing={missing}, unexpected={unknown}')
    frame['half_day']=False
    for day in frame.index:
        if day in sched.index:
            frame.loc[day,'half_day']=(sched.loc[day,'close']-sched.loc[day,'open']).total_seconds()<5*3600
    # Price high/low definitions can differ around auctions. Preserve raw in provider snapshots.
    frame['high_observed']=frame[['high','open','close']].max(axis=1,skipna=False)
    frame['low_observed']=frame[['low','open','close']].min(axis=1,skipna=False)
    return frame, {'price_conflicts':conflicts,'missing_sessions':missing,'unexpected_sessions':unknown,
        'unpaired_dates':[v.date().isoformat() for v in unmatched],'calendar_overrides':MARKET_CLOSURES,
        'daily_count':int((frame.index>=pd.Timestamp(asof)-pd.DateOffset(years=3)).sum()),
        'full_count':len(frame),'downloaded_long_history_count':len(y),'resolved_conflict_count':len(resolved),
        'training_source':'Eastmoney raw OHLCV from 2023-01-05; Yahoo + Tencent cross-check; unresolved dates quarantined',
        'turnover_unit':'HKD inferred from vendor quote and price-volume consistency; not independently licensed',
        'volume_difference_latest':float(pair.volume.iloc[-1]-pair.volume_em.iloc[-1]),
        'adjustment':'Pre-2023 adjustment mismatch excluded; recent raw OHLC; dividend-crossing labels excluded',
        'coverage_note':'Daily extrema include observable O/C; auction path not fully verified'}

def feature_table(df,raw_dir,asof):
    raw_close=df.close
    c=wealth_index(raw_close,df.dividend_amount); f=pd.DataFrame(index=df.index)
    ret=c.pct_change(fill_method=None)
    for n in [1,3,5,10,20,60]: f[f'ret_{n}']=c.pct_change(n,fill_method=None)
    for n in [5,10,20,60,120,250]:
        df[f'ma{n}']=raw_close.rolling(n,min_periods=n).mean()
        f[f'ma_distance_{n}']=c/c.rolling(n,min_periods=n).mean()-1
    for n in [5,10,20]: f[f'ma_slope_{n}']=c.rolling(n).mean().pct_change(5,fill_method=None)
    tr=pd.concat([df.high_observed-df.low_observed,(df.high_observed-raw_close.shift()).abs(),(df.low_observed-raw_close.shift()).abs()],axis=1).max(axis=1)
    df['atr14']=tr.rolling(14,min_periods=14).mean()
    adjusted_high=df.high_observed*c/raw_close;adjusted_low=df.low_observed*c/raw_close
    adjusted_tr=pd.concat([adjusted_high-adjusted_low,(adjusted_high-c.shift()).abs(),(adjusted_low-c.shift()).abs()],axis=1).max(axis=1)
    f['atr_pct']=adjusted_tr.rolling(14,min_periods=14).mean()/c
    for n in [20,60]: f[f'vol_{n}']=ret.rolling(n,min_periods=n).std()*np.sqrt(252)
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    df['rsi14']=100-100/(1+gain/loss); f['rsi14']=df.rsi14/100
    df['macd']=raw_close.ewm(span=12,adjust=False).mean()-raw_close.ewm(span=26,adjust=False).mean()
    df['macd_signal']=df.macd.ewm(span=9,adjust=False).mean()
    f['macd_pct']=(c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean())/c
    f['volume_ratio']=df.volume/df.volume.shift().rolling(20).mean()
    f['turnover_ratio']=df.turnover/df.turnover.shift().rolling(20).mean()
    f['turnover_rate']=df.turnover_rate
    f['gap']=(df.open+df.dividend_amount)/raw_close.shift()-1
    f['intraday']=raw_close/df.open-1
    f['range_position']=(raw_close-df.low_observed)/(df.high_observed-df.low_observed).replace(0,np.nan)
    f['drawdown_60']=c/c.rolling(60).max()-1
    f['drawdown_250']=c/c.rolling(250).max()-1
    f['half_day']=df.half_day.astype(int); f['dividend_day']=df.dividend.astype(int)
    assets=[]
    cutoffs=pd.DatetimeIndex(df.index).tz_localize('Asia/Hong_Kong')+pd.Timedelta(hours=18,minutes=30)
    for symbol,(label,market) in ASSETS.items():
        if symbol=='0700.HK': continue
        path=raw_dir/(symbol.replace('^','index-').replace('=','-')+'.json')
        if not path.exists(): continue
        af,result,raw=yahoo_frame(path)
        # Conservative completed-session input. Foreign same-date bars never enter a HK close model.
        valid=af.index<=pd.Timestamp(asof) if market=='HK' else af.index<pd.Timestamp(asof)
        af=af.loc[valid]
        if len(af)<6: continue
        close=af.close
        feature_close=wealth_index(close,dividend_amounts(af.index,result.get('events',{}),result['meta']['exchangeTimezoneName']))
        if market=='HK': available=af.index.tz_localize('Asia/Hong_Kong')+pd.Timedelta(hours=17)
        elif market=='US': available=(af.index.tz_localize('America/New_York')+pd.Timedelta(hours=18)).tz_convert('Asia/Hong_Kong')
        else: available=(af.index.tz_localize('UTC')+pd.Timedelta(days=1,hours=2)).tz_convert('Asia/Hong_Kong')
        rates=pd.DataFrame({'available':available,'r1':feature_close.pct_change(fill_method=None).to_numpy(),'r5':feature_close.pct_change(5,fill_method=None).to_numpy(),'obs':af.index})
        joined=pd.merge_asof(pd.DataFrame({'cutoff':cutoffs}),rates.sort_values('available'),left_on='cutoff',right_on='available',direction='backward')
        safe_name=symbol.replace('^','').replace('=','').replace('.','_').replace('-','_')
        if symbol in ['^HSI','3033.HK','QQQ','KWEB','^VIX','DX-Y.NYB','CNH=X','CL=F','GC=F','HYG','TLT']:
            f[f'{safe_name}_r1']=joined.r1.to_numpy(); f[f'{safe_name}_r5']=joined.r5.to_numpy()
        latest=close.iloc[-1]
        assets.append({'symbol':symbol,'name':label,'market':market,'date':af.index[-1].date().isoformat(),
            'value':latest,'change_1d':100*(latest/close.iloc[-2]-1),'change_5d':100*(latest/close.iloc[-6]-1),
            'source_url':f'https://finance.yahoo.com/quote/{urllib.parse.quote(symbol,safe="")}/',
            'available_at':available[-1].isoformat(),'fetched_at':raw['fetched_at'],
            'note':'期货连续合约可能含换月影响' if '=F' in symbol else '使用已完成交易时段'})
    return f,assets

def make_labels(df):
    result={}
    for h in HORIZONS:
        target=pd.DataFrame(index=df.index,columns=list(TARGETS)+['first_hit'],dtype=float)
        for i in range(len(df)-h):
            window=df.iloc[i:i+h+1]; future=window.iloc[1:]; p=df.close.iloc[i]
            if window[['open','close','high_observed','low_observed']].isna().any().any() or window['conflict'].any() or future.dividend.any(): continue
            peak=window.close.cummax()
            up=max(0,future.high_observed.max()/p-1); down=max(0,1-future.low_observed.min()/p)
            hit=0
            for row in future.itertuples():
                if row.open>=p*1.05:hit=1;break
                if row.open<=p*.95:hit=-1;break
                u=row.high_observed>=p*1.05; d=row.low_observed<=p*.95
                if u or d: hit=2 if u and d else 1 if u else -1; break
            target.iloc[i]=[future.close.iloc[-1]/p-1,up,down,(1-window.close/peak).max(),hit]
        result[h]=target
    return result

def resample(df,period):
    cols={'open':'first','high_observed':'max','low_observed':'min','close':'last','volume':'sum','turnover':'sum'}
    bars=df.resample(period).agg(cols).dropna(subset=['close'])
    for n in [5,10,20]: bars[f'ma{n}']=bars.close.rolling(n).mean()
    bars['date']=bars.index.strftime('%Y-%m-%d')
    bars['partial']=bars.index>df.index[-1]
    return bars.to_dict(orient='records')

def quantile_loss(y,pred): return float(np.mean([mean_pinball_loss(y,pred[:,k],alpha=q) for k,q in enumerate(QUANTILES)]))

def train_target(x,y,h,target,first_test):
    idx=np.arange(len(x)); predictions=[]; current=None; metrics=[]
    test_starts=list(range(first_test,len(x)-h,TEST_BLOCK))
    origins=test_starts+[len(x)]
    for start in origins:
        cal_end=start-h
        cal_start=cal_end-CALIBRATION
        train_end=cal_start-h
        train_start=max(250,train_end-MAX_TRAIN)
        train=idx[(idx>=train_start)&(idx<train_end)&y.notna().to_numpy()]
        calibration=idx[(idx>=cal_start)&(idx<cal_end)&y.notna().to_numpy()]
        test=idx[(idx>=start)&(idx<min(start+TEST_BLOCK,len(x)-h))&y.notna().to_numpy()]
        current_mode=start==len(x)
        if len(train)<200 or len(calibration)<45 or (not current_mode and len(test)==0): continue
        selected=np.array([len(x)-1]) if current_mode else test
        models=[]; forecast=[]; cal_forecast=[]
        for q in QUANTILES:
            model=LGBMRegressor(objective='quantile',alpha=q,n_estimators=110,num_leaves=7,max_depth=3,
                min_child_samples=60,learning_rate=.035,reg_lambda=5,reg_alpha=.1,feature_fraction=.8,
                random_state=42,n_jobs=2,verbosity=-1)
            model.fit(x.iloc[train],y.iloc[train])
            forecast.append(model.predict(x.iloc[selected])); cal_forecast.append(model.predict(x.iloc[calibration])); models.append(model)
        pred=np.sort(np.array(forecast).T,axis=1); cp=np.sort(np.array(cal_forecast).T,axis=1)
        raw_pred=pred.copy()
        scores=np.maximum(cp[:,0]-y.iloc[calibration].to_numpy(),y.iloc[calibration].to_numpy()-cp[:,2])
        correction=max(0,float(np.quantile(scores,min(1,math.ceil((len(scores)+1)*.8)/len(scores)),method='higher')))
        pred[:,0]-=correction; pred[:,2]+=correction
        if target!='return': pred=np.maximum(pred,0)
        # Recent unconditional empirical distribution; fitted only on mature historical labels.
        history=idx[(idx>=max(250,start-h-504))&(idx<start-h)&y.notna().to_numpy()]
        base=np.tile(np.quantile(y.iloc[history],QUANTILES),(len(selected),1))
        if current_mode:
            current={'lightgbm':raw_pred[0].tolist(),'calibrated_interval':[float(pred[0,0]),float(pred[0,2])],'empirical':base[0].tolist(),'training_n':len(train),'calibration_n':len(calibration),'calibration_expansion':correction,
                'latest_training_date':x.index[train[-1]].date().isoformat(),'latest_calibration_date':x.index[calibration[-1]].date().isoformat()}
        else:
            truth=y.iloc[test].to_numpy(); lp=quantile_loss(truth,raw_pred); bp=quantile_loss(truth,base)
            metrics.append({'start':x.index[test[0]].date().isoformat(),'end':x.index[test[-1]].date().isoformat(),'n':len(test),'lightgbm_pinball':lp,'empirical_pinball':bp,
                'coverage80':float(np.mean((truth>=pred[:,0])&(truth<=pred[:,2]))),'width':float(np.mean(pred[:,2]-pred[:,0]))})
            predictions.extend({'date':x.index[j].date().isoformat(),'actual':float(y.iloc[j]),'model':raw_pred[k].tolist(),'calibrated_interval':[float(pred[k,0]),float(pred[k,2])],'baseline':base[k].tolist()} for k,j in enumerate(test))
    if not predictions: return {'status':'insufficient_samples','current':current,'folds':metrics},[]
    ys=np.array([p['actual'] for p in predictions]); ps=np.array([p['model'] for p in predictions]); bs=np.array([p['baseline'] for p in predictions])
    intervals=np.array([p['calibrated_interval'] for p in predictions])
    lp=quantile_loss(ys,ps); bp=quantile_loss(ys,bs)
    # No automatic promotion after one exploratory holdout. Keep both candidates visible.
    return {'status':'experimental_not_promoted','current':current,'oos_n':len(ys),'lightgbm_pinball':lp,'empirical_pinball':bp,
        'improvement_pct':100*(bp-lp)/bp,'coverage80':float(np.mean((ys>=intervals[:,0])&(ys<=intervals[:,1]))),
        'interval_width':float(np.mean(intervals[:,1]-intervals[:,0])),'folds_won':sum(m['lightgbm_pinball']<m['empirical_pinball'] for m in metrics),'fold_count':len(metrics),'folds':metrics},predictions

def analogs(x,labels):
    cols=['ret_5','ret_20','ma_distance_20','ma_distance_60','vol_20','volume_ratio','gap','range_position']
    latest=x.iloc[-1][cols]; results=[]
    for h in HORIZONS:
        hist=x.iloc[250:-h].copy(); valid=labels[h].loc[hist.index].dropna().index
        hist=hist.loc[valid].dropna(subset=cols)
        if hist.empty: continue
        scale=hist[cols].std().replace(0,1); distances=(((hist[cols]-latest)/scale)**2).mean(axis=1).pow(.5).sort_values()
        chosen=[]
        for date,distance in distances.items():
            position=x.index.get_loc(date)
            if all(abs(position-other[2])>=h for other in chosen): chosen.append((date,float(distance),position))
            if len(chosen)>=40: break
        values=labels[h].loc[[v[0] for v in chosen]]
        summary={t:np.quantile(values[t],QUANTILES).tolist() for t in TARGETS}
        hits=values.first_hit.value_counts(); n=len(values)
        results.append({'horizon':h,'n':n,'note':'历史相似状态描述，未通过独立预测验证；按窗口间隔取样但并非完全独立',
            'quantiles':summary,'positive_rate':float((values['return']>0).mean()),
            'first_up_5_lower':float(hits.get(1,0)/n),'first_up_5_upper':float((hits.get(1,0)+hits.get(2,0))/n),
            'ambiguous_rate':float(hits.get(2,0)/n),'examples':[{'date':d.date().isoformat(),'distance':s,**values.loc[d].to_dict()} for d,s,_ in chosen[:10]]})
    return results

def main():
    p=argparse.ArgumentParser(); p.add_argument('--date',required=True); p.add_argument('--skip-model',action='store_true'); a=p.parse_args()
    root=ROOT/'research-private'/f'tencent-{a.date}'; raw=root/'raw'
    df,quality=normalize(raw,a.date); x,assets=feature_table(df,raw,a.date); labels=make_labels(df)
    quality['unavailable_assets']=[symbol for symbol in ASSETS if symbol!='0700.HK' and symbol not in {v['symbol'] for v in assets}]
    quality['failed_sources']=load(raw/'collection.json').get('errors',[])
    features=x.replace([np.inf,-np.inf],np.nan)
    # Limit experimental headline target to exact market data features; no fabricated historical news.
    forecasts=[]; backtests={}
    if not a.skip_model:
        for h in HORIZONS:
            item={'horizon':h,'targets':{}}
            for target in TARGETS:
                print('fit',h,target,flush=True)
                summary,preds=train_target(features,labels[h][target],h,target,max(650,len(df)-126))
                item['targets'][target]=summary; backtests[f'{h}_{target}']=preds
            forecasts.append(item)
    # Full series and derived bars remain in the private snapshot / local viewer only.
    recent=df.loc[pd.Timestamp(a.date)-pd.DateOffset(years=3):].copy()
    daily=recent.reset_index(names='date'); daily['date']=daily.date.dt.strftime('%Y-%m-%d')
    last=df.iloc[-1]; prev=df.close.iloc[-2]
    technical={'date':a.date,'close':last.close,'open':last.open,'high':last.high_observed,'low':last.low_observed,
        'change_1d':100*(last.close/prev-1),'volume':last.volume,'turnover':last.turnover,'ma':{str(n):last[f'ma{n}'] for n in [5,10,20,60,120,250]},
        'atr14':last.atr14,'rsi14':last.rsi14,'macd':last.macd,'macd_signal':last.macd_signal,
        'volume_ratio':x.volume_ratio.iloc[-1],'gap_pct':x.gap.iloc[-1]*100,'range_position':x.range_position.iloc[-1],
        'return_5d':(df.close.iloc[-1]/df.close.iloc[-6]-1)*100,'return_20d':(df.close.iloc[-1]/df.close.iloc[-21]-1)*100,'drawdown_250':(df.close.iloc[-1]/df.close.iloc[-250:].max()-1)*100,
        'recent_high_20':df.high_observed.iloc[-21:-1].max(),'recent_low_20':df.low_observed.iloc[-21:-1].min()}
    macro=[]
    for series,label in FRED.items():
        path=raw/f'fred-{series}.json'
        if not path.exists(): continue
        payload=load(path); data=pd.read_csv(io.StringIO(payload['csv'])); data.columns=['date','value']; data['value']=pd.to_numeric(data.value,errors='coerce'); data=data.dropna(); data=data[data.date<=a.date]
        if len(data): macro.append({'series':series,'name':label,**data.iloc[-1].to_dict(),'source_url':f'https://fred.stlouisfed.org/series/{series}','note':'最新修订快照，仅用于当前解释，未进入历史回测'})
    result={'schema_version':1,'symbol':'0700.HK','report_date':a.date,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'feature_cutoff':a.date+'T18:30:00+08:00','research_cutoff':dt.datetime.now(dt.timezone.utc).isoformat(),
        'technical':technical,'assets':assets,'macro':macro,'quality':quality,'forecasts':forecasts,'analogs':analogs(features,labels),
        'chart':{'daily':daily.to_dict(orient='records'),'weekly':resample(df,'W-FRI')[-160:],'monthly':resample(df,'ME')[-40:]},
        'model_protocol':{'features':list(features.columns),'feature_count':len(features.columns),'horizons':list(HORIZONS),'quantiles':list(QUANTILES),
            'validation':'Frozen small LightGBM configuration; chronological quarterly blocks; 126-day calibration; h-day purge at each boundary',
            'test_first_index':max(650,len(df)-126),'selection':'Research candidates only; no promotion or calibrated directional probability claimed',
            'limitations':['Today news is not a historically validated feature','Overlapping target observations are not independent','No transaction-cost strategy backtest','No neural model','No point-in-time macro revisions in model','Historical availability timestamps are conservative reconstructed cutoffs, not archived vendor publication timestamps']}}
    save(root/'analysis.json',result); save(root/'backtests.json',backtests)
    features.to_pickle(root/'features.pkl'); df.to_pickle(root/'daily.pkl')
    print(json.dumps(clean({'technical':technical,'conflicts':len(quality['price_conflicts']),'resolved':quality['resolved_conflict_count'],'training_rows':len(df),'features':len(features.columns),'macro_count':len(macro)}),ensure_ascii=False,indent=2))

if __name__=='__main__':
    import urllib.parse
    main()
