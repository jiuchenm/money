"""Intraday data quality, session-aware aggregation and finite three-day scenarios."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import hashlib
import math
from pathlib import Path
import concurrent.futures
import urllib.parse
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from collect import ROOT,fetch
from trading_calendar import connect_open,next_connect_sessions,SOURCE as CONNECT_SOURCE

HKT='Asia/Hong_Kong'

def safe(value):
    if isinstance(value,dict):return {str(k):safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [safe(v) for v in value]
    if isinstance(value,np.generic):return safe(value.item())
    if isinstance(value,(pd.Timestamp,dt.datetime,dt.date)):return value.isoformat()
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(safe(value),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def collect_intraday(folder):
    folder.mkdir(parents=True,exist_ok=True)
    urls={
      'yahoo30':'https://query1.finance.yahoo.com/v8/finance/chart/0700.HK?interval=30m&range=60d',
      'tencent30':'https://web.ifzq.gtimg.cn/appstock/app/kline/mkline?param=hk00700,m30,,640',
      'eastmoney30':'https://33.push2his.eastmoney.com/api/qt/stock/kline/get?secid=116.00700&klt=30&fqt=0&beg=0&end=20500000&lmt=1000&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
    }
    def one(name,url):
        value={'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'source_url':url,'payload':json.loads(fetch(url))}
        save(folder/(name+'.json'),value);return name
    errors=[];succeeded=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(one,k,v):k for k,v in urls.items()}
        for j in concurrent.futures.as_completed(jobs):
            try:
                name=j.result();succeeded.append(name);print(name,'OK')
            except Exception as e:
                name=jobs[j];errors.append({'source':name,'error':str(e)[:180]})
                print(name,type(e).__name__,str(e)[:180])
                stale=folder/(name+'.json')
                if stale.exists():
                    archive=folder/'prior-attempts';archive.mkdir(exist_ok=True)
                    stale.replace(archive/(name+'-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.json'))
    save(folder/'collection.json',{'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'succeeded':succeeded,'errors':errors})
    if 'yahoo30' not in succeeded:raise ValueError('No fresh primary minute response')

def add_indicators(frame):
    f=frame.copy();c=f.close
    for n in [5,10,20]:
        f[f'ma{n}']=c.rolling(n,min_periods=n).mean()
        f[f'ema{n}']=c.ewm(span=n,adjust=False,min_periods=n).mean()
    diff=c.diff();gain=diff.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean();loss=(-diff.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    f['rsi14']=100-100/(1+gain/loss)
    f['prior4low']=f.low.shift().rolling(4).min();f['prior4high']=f.high.shift().rolling(4).max()
    f['ema10_slope']=f.ema10.diff()
    return f

def aggregate120(frame):
    full=[];residual=[]
    for date,day in frame.groupby(frame.index.date):
        for start,end,expected in [('09:30','11:30',4),('11:30','12:00',1),('13:00','15:00',4),('15:00','16:00',2)]:
            left=pd.Timestamp(str(date)+' '+start,tz=HKT);right=pd.Timestamp(str(date)+' '+end,tz=HKT)
            part=day[(day.index>=left)&(day.index<right)]
            if len(part)!=expected:continue
            row={'timestamp':left,'bar_end':right,'date':left.isoformat(),'open':part.open.iloc[0],
              'high':part.high.max(),'low':part.low.min(),'close':part.close.iloc[-1],
              'volume':part.volume.sum(),'turnover':part.turnover.sum(min_count=len(part)),
              'duration_minutes':expected*30,'partial':expected!=4}
            (full if expected==4 else residual).append(row)
    return add_indicators(pd.DataFrame(full).set_index('timestamp')),residual

def load_bars(folder,cutoff):
    raw=json.loads((folder/'yahoo30.json').read_text(encoding='utf-8'))
    cutoff=min(cutoff,pd.Timestamp(raw['fetched_at'])-pd.Timedelta(minutes=20))
    result=raw['payload']['chart']['result'][0]
    frame=pd.DataFrame(result['indicators']['quote'][0],index=pd.to_datetime(result['timestamp'],unit='s',utc=True).tz_convert(HKT))
    if frame.index.has_duplicates:raise ValueError('Duplicate intraday timestamps')
    hm=frame.index.strftime('%H:%M')
    continuous=((hm>='09:30')&(hm<'12:00'))|((hm>='13:00')&(hm<'16:00'))
    cas=frame[(hm=='16:00')&(frame.index+pd.Timedelta(minutes=10)<=cutoff)].dropna().copy()
    bars=frame[continuous].dropna(subset=['open','high','low','close','volume']).copy()
    bars=bars[(bars.index+pd.Timedelta(minutes=30))<=cutoff]
    if ((bars.low>bars[['open','close']].min(axis=1))|(bars.high<bars[['open','close']].max(axis=1))|(bars.volume<0)).any():
        raise ValueError('Invalid OHLCV')
    counts=bars.groupby(bars.index.date).size()
    invalid_days=counts[counts!=11]
    # Current source window contains full sessions; fail rather than invent missing bars.
    if len(invalid_days):raise ValueError(f'Incomplete sessions: {invalid_days.to_dict()}')
    bars['turnover']=np.nan
    conflicts=[];compared=0;volume_ratios=[];crosscheck_latest=None;current_checked=0
    em_path=folder/'eastmoney30.json'
    if em_path.exists():
        em=json.loads(em_path.read_text(encoding='utf-8'))['payload']['data']['klines']
        for line in em:
            v=line.split(',');end=pd.Timestamp(v[0],tz=HKT);start=end-pd.Timedelta(minutes=30)
            if start not in bars.index:continue
            # EM's last bar includes CAS; don't attach its volume/amount to Yahoo continuous bar.
            if start.strftime('%H:%M')=='15:30':continue
            compared+=1;ec=float(v[2]);yc=float(bars.loc[start,'close'])
            crosscheck_latest=max(crosscheck_latest or start.date(),start.date())
            if start.date()==bars.index[-1].date():current_checked+=1
            if abs(ec-yc)>.011:conflicts.append({'time':start.isoformat(),'yahoo_close':yc,'eastmoney_close':ec})
            bars.loc[start,'turnover']=float(v[6])
            if float(v[5])>0:volume_ratios.append(float(bars.loc[start,'volume'])/float(v[5]))
    bars['bar_end']=bars.index+pd.Timedelta(minutes=30);bars['date']=bars.index.map(lambda t:t.isoformat());bars['duration_minutes']=30
    bars=add_indicators(bars)
    f120,residual=aggregate120(bars)
    quality={'source_url':raw['source_url'],'fetched_at':raw['fetched_at'],'raw_slots':len(frame),
      'continuous_bars':len(bars),'trading_days':len(counts),'first_bar':bars.index[0].isoformat(),
      'last_bar_start':bars.index[-1].isoformat(),'last_bar_end':bars.bar_end.iloc[-1].isoformat(),
      'closing_auction_points':len(cas),'excluded_lunch_slots':int(((hm>='12:00')&(hm<'13:00')).sum()),
      'crosschecked_price_bars':compared,'price_conflicts':conflicts,
      'crosscheck_last_market_date':str(crosscheck_latest) if crosscheck_latest else None,
      'current_day_crosschecked_bars':current_checked,
      'crosscheck_status':'current' if current_checked else 'historical_only' if compared else 'unavailable',
      'median_volume_ratio_yahoo_to_eastmoney':float(np.median(volume_ratios)) if volume_ratios else None,
      'turnover_note':'30m成交额仅采用可对齐Eastmoney bar；末根含竞价口径不一致时留空，不用价格乘量冒充。'+(' 当前日没有第二源，成交额缺失。' if not current_checked else ''),
      'aggregation_policy':'120m仅09:30–11:30和13:00–15:00；上午剩30m和下午剩60m单列，不能作完整120m信号。',
      'auction_note':'Yahoo16:00单点为收盘竞价；连续交易末根收盘不一定等于日线收盘。',
      'distribution_note':'研究展示使用公开事实行情，来源与时点显式保留；不是授权数据服务。'}
    return bars,f120,residual,cas,quality

def wilson(wins,n):
    if n==0:return None
    z=1.959964;p=wins/n;den=1+z*z/n;center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,center-half),min(1,center+half)]

def fee_estimate(price,shares,commission_rate=.0003,min_commission=15,slippage=.0005):
    value=price*shares
    official=math.ceil(value*.001)+sum(round(value*r,2) for r in [.0000565,.000027,.0000015,.000042])
    return {'official_hkd':official,'commission_assumed_hkd':max(min_commission,value*commission_rate),
      'slippage_assumed_hkd':value*slippage,'total_assumed_hkd':official+max(min_commission,value*commission_rate)+value*slippage}

def simulate(frame,daily,start_day,lots,rebuy,triggered,cost=.002):
    days=sorted(set(frame.index.date));begin=days.index(start_day);episode_days=days[begin:begin+3]
    if len(episode_days)!=3:raise ValueError('Immature episode')
    future=frame[np.isin(frame.index.date,episode_days)]
    end_price=float(daily.loc[str(episode_days[-1]),'close'])
    prior=daily[daily.index<pd.Timestamp(start_day)]
    atr=float(prior.atr14.iloc[-1]);shares=300;cash=0.;sold=0;rebought=0;pending=False;targets=[];sell_price=None
    for ordinal,(time,row) in enumerate(future.iterrows()):
        if not connect_open(time.date(),time.time()):continue
        if sold==0 and ((not triggered and ordinal==0) or pending):
            sell_price=float(row.open);quantity=lots*100;cash+=quantity*sell_price*(1-cost);shares-=quantity;sold=lots;pending=False
            raw_targets=[sell_price-(j+1)*.5*atr for j in range(lots)] if rebuy else []
            if any(not 200<=v<500 for v in raw_targets):
                raise ValueError('Price moved outside audited tick band; review HKEX tick schedule before simulation')
            targets=[round(math.floor(v/.2)*.2,2) for v in raw_targets]
            continue # no same-bar sell and intrabar buyback assumptions
        if targets:
            remaining=[]
            for level in targets:
                # Resting limit: gap price improvement, otherwise require strict penetration.
                fill=float(row.open) if row.open<level else level if row.low<level-.001 else None
                if fill is not None and cash>=100*fill*(1+cost):cash-=100*fill*(1+cost);shares+=100;rebought+=1
                else:remaining.append(level)
            targets=remaining
        if triggered and sold==0 and bool(row.sell_trigger):pending=True
    delta=cash+shares*end_price-300*end_price
    return {'start':str(start_day),'end':str(episode_days[-1]),'delta_hkd':delta,'sold_lots':sold,'rebought_lots':rebought,
      'ending_lots':shares//100,'sell_price':sell_price,'end_price':end_price,'triggered':sold>0,
      'unrecovered_lots':sold-rebought,'remaining_cash':cash}

def strategy_statistics(bars,f120,daily):
    # Every signal uses a previously completed day/120m bar and its own completed 30m bar.
    right=f120[['bar_end','close','ema10','ema10_slope']].rename(columns={'close':'h2close','ema10':'h2ema10','ema10_slope':'h2slope'})
    joined=pd.merge_asof(bars.reset_index(names='start').sort_values('bar_end'),right.sort_values('bar_end'),on='bar_end',direction='backward').set_index('start')
    daily_weak=[];daily_state=[]
    for time in joined.index:
        past=daily[daily.index<pd.Timestamp(time.date())]
        if len(past)<20:daily_weak.append(False);daily_state.append('unknown');continue
        prev=past.iloc[-1];weak=prev.close<prev.ma10 and prev.ma10<past.ma10.iloc[-4]
        daily_weak.append(bool(weak));daily_state.append('up' if prev.close>prev.ma20 else 'down')
    joined['daily_weak']=daily_weak;joined['daily_state']=daily_state
    joined['sell_trigger']=(joined.close<joined.prior4low)&(joined.h2close<joined.h2ema10)&(joined.h2slope<0)
    days=sorted(set(joined.index.date))
    starts=days[20:-2:3] # frozen non-overlapping starts, no outcome-based selection
    variants=[(n,rebuy,trig) for trig in [False,True] for rebuy in [False,True] for n in [1,2,3]]
    stats=[];all_records={}
    current_state='up' if daily.close.iloc[-1]>daily.ma20.iloc[-1] else 'down'
    for lots,rebuy,trig in variants:
        key=f'{"confirm" if trig else "open"}-{lots}-{ "rebuy" if rebuy else "cash"}'
        rows=[simulate(joined,daily,d,lots,rebuy,trig) for d in starts]
        wins=sum(r['delta_hkd']>1 for r in rows);losses=sum(r['delta_hkd']<-1 for r in rows);n=len(rows)
        active=[r for r in rows if r['triggered']]
        matched=[r for r in rows if joined[joined.index.date==dt.date.fromisoformat(r['start'])].daily_state.iloc[0]==current_state]
        sensitivity={str(c):float(np.mean([simulate(joined,daily,d,lots,rebuy,trig,c)['delta_hkd'] for d in starts])) for c in [.0015,.003]}
        stats.append({'id':key,'sell_lots':lots,'rebuy':rebuy,'triggered_rule':trig,'n':n,'wins':wins,'losses':losses,'ties':n-wins-losses,
          'win_rate':wins/n if n else None,'wilson95':wilson(wins,n),'mean_delta_hkd':np.mean([r['delta_hkd'] for r in rows]) if n else None,
          'median_delta_hkd':np.median([r['delta_hkd'] for r in rows]) if n else None,'worst_delta_hkd':min([r['delta_hkd'] for r in rows],default=None),
          'action_count':len(active),'conditional_win_rate':sum(r['delta_hkd']>1 for r in active)/len(active) if active else None,
          'same_daily_state_n':len(matched),'same_daily_state_wins':sum(r['delta_hkd']>1 for r in matched),
          'unrecovered_episodes':sum(r['unrecovered_lots']>0 for r in rows),'fee_sensitivity_mean_hkd':sensitivity,
          'status':'insufficient_evidence_not_recommendation'})
        all_records[key]=rows
    return stats,all_records,joined

def create_analysis(folder,report_date):
    now=pd.Timestamp.now(tz='UTC');bars,h2,residual,cas,quality=load_bars(folder,now-pd.Timedelta(minutes=20))
    daily_root=ROOT/'research-private'/f'tencent-{report_date}'
    daily=pd.read_pickle(daily_root/'daily.pkl')
    if bars.index[-1].date().isoformat()!=report_date or cas.empty or cas.index[-1].date().isoformat()!=report_date:
        raise ValueError('Intraday/CAS and daily dates differ')
    if abs(float(cas.close.iloc[-1])-float(daily.close.iloc[-1]))>.011:
        raise ValueError('Closing auction and daily close disagree')
    stats,records,joined=strategy_statistics(bars,h2,daily)
    last=bars.iloc[-1];last2=h2.iloc[-1];lastd=daily.iloc[-1]
    future=next_connect_sessions(report_date)
    levels={'resistance_1':[453.8,454.2],'resistance_2':[458.4,463.4],'support_1':[449.0,449.2],
      'support_2':[442.0,442.8],'support_3':[431.7,437.4],'daily_invalidation':430.0,
      'derivation':'当前30m最近整理低点449.2/反弹区454，午前458–463供给区；日线跳空442–442.8和MA10/20区域。静态观察位，触发前随新bar更新。'}
    outcome={'schema_version':1,'as_of':now.isoformat(),'market_date':report_date,'forecast_sessions':[v.date().isoformat() for v in future],
      'position':{'lots':3,'shares_per_lot':100,'shares':300,'cost_hkd':428,'last_daily_close':float(lastd.close),
        'gross_price_pnl_hkd':float((lastd.close-428)*300),'public_authorization':'User explicitly requested full page and 3-lot position planning on 2026-09-23'},
      'quality':quality,'levels':levels,
      'execution_calendar':{'source_url':CONNECT_SOURCE,'report_day_connect_open':connect_open(report_date),
        'note':'港股行情日与港股通可交易日不同。2026-09-25港股开市但港股通关闭；后续三次可执行交易日按港股通日历筛选。'},
      'state':{'m30':{k:last[k] for k in ['close','ma5','ma10','ma20','ema10','ema10_slope','rsi14','prior4low','prior4high']},
        'h120':{k:last2[k] for k in ['close','ma5','ma10','ma20','ema10','ema10_slope','rsi14']},
        'daily':{'close':lastd.close,'ma5':lastd.ma5,'ma10':lastd.ma10,'ma20':lastd.ma20,'ma60':lastd.ma60,'atr14':lastd.atr14},
        'last120_end':last2.bar_end,'last30_end':last.bar_end,'last_cas_close':float(cas.close.iloc[-1]),
        'sell_trigger_now':bool(joined.sell_trigger.iloc[-1]),'daily_weak_now':bool(lastd.close<lastd.ma10 and lastd.ma10<daily.ma10.iloc[-4])},
      'strategy_statistics':stats,
      'fee_reference':{'official_rate_per_side_pct':.1127,'commission_rate_assumed':.0003,'minimum_commission_hkd_assumed':15,
        'slippage_rate_assumed':.0005,'sell_one_lot_at_close':fee_estimate(float(lastd.close),100),
        'sources':['https://static.www.tencent.com/storage/uploads/2019/11/09/e4c1b849acb21fb78fcb7c223bab5675.pdf',
          'http://www.sse.com.cn/services/charge/hkexsc/','https://www.hkex.com.hk/News/Market-Communications/2025/250221news?sc_lang=en'],
        'note':'每手100股；佣金和滑点是可编辑假设，未取得券商实际费率。港股通人民币汇率损益另算。'},
      'protocol':{'benchmark':'未来三个交易日期末净财富相对始终持有300股的增量；不是相对成本428的盈利概率',
        'rule':'等待确认：完整120m收盘低于EMA10且EMA10下降；完整30m收盘跌破此前4根最低价；下一根开盘卖出。日线状态用于分层，未据结果调参。',
        'rebuy_rule':'只买回已卖数量；卖出价下方0.5/1/1.5倍前日ATR各1手，按当前价档0.2港币向下取整；卖出所在30m整根不买回，最早下一根挂单，严格穿价才成交；只参与连续交易，CAS仅用于期末估值。三日期末未买回保留现金并计踏空。',
        'cost_assumption':'每边总摩擦0.20%，含费用与滑点的压力假设；另测0.15%/0.30%。券商最低佣金、人民币汇兑和实际费用未知，非真实账单。',
        'sample_design':'前20交易日预热，之后每3个交易日一个固定起点，不重叠窗口；首次探索性回放，未做独立最终测试。',
        'uncertainty':'Wilson区间仅为小样本二项参考，市场相关性/规则挑选会增加不确定性；经验频率不是未来可靠获胜概率。',
        'probability_status':'样本不足，所有动作保持实验状态；卖出1/2/3手的胜负通常相同，金额与踏空风险不同。'},
      'chart':{'m30':bars.reset_index(drop=True).rename(columns={'high':'high_observed','low':'low_observed'}).to_dict(orient='records'),
        'h120':h2.reset_index(drop=True).rename(columns={'high':'high_observed','low':'low_observed'}).to_dict(orient='records'),
        'residual':residual},
      'plan':{'headline':'先保留3手；未来三日按30m触发分批做T，未确认不因一根长阳清仓。',
        'reason':'日线站上MA20；完整120m收450.2、高于EMA10约437.62且均线向上。30m收450.6，高于EMA10约449.92但低于MA10约454.64，早盘急拉后横盘。当前卖出触发为否。',
        'days':[{'date':future[0].date().isoformat(),'focus':'先确认30m能否守449.2并收复454；开盘跳空后至少等第一根完整30m。','default':'没有转弱触发则持3手；触发才考虑减1手。'},
          {'date':future[1].date().isoformat(),'focus':'核对第1天高低点与完整120m方向，不照搬昨日静态价位。','default':'442有效失守且120m转弱时才讨论累计减2手；回踩止跌则先买回1手。'},
          {'date':future[2].date().isoformat(),'focus':'比较三日期末净财富与始终持3手，包含未买回的现金与踏空。','default':'保留最后1手或清仓取决于日线430失守及多周期共振；不得为了完成计划强行交易。'}],
        'actions':[
          {'name':'减1手','trigger':'反弹至454–458受阻，30m收盘重新跌破449.2；或30m跌破此前4根低点且完整120m转弱。','action':'下一根可交易bar观察卖1手，余2手。成交后才建立买回单。','rebuy':'442–443附近先看30m止跌收复EMA5；确认后买回1手，上限3手。','cancel':'30m收复454且120m保持上行，则取消弱势减仓情景。'},
          {'name':'累计减2手','trigger':'第一手已减后，完整120m收在442以下，30m反抽442失败。','action':'再减1手，累计卖2手，余1手；不是重复卖2手。','rebuy':'第一手观察442重新收复，第二手观察437–432止跌；每次需30m确认，不盲挂抄底。','cancel':'重新收复452且120m不再下行，减仓理由减弱。'},
          {'name':'清仓3手','trigger':'日线收盘跌破430，且120m与30m同时延续下降。','action':'才讨论处理最后1手；三日里没发生就不执行，跳空时实际成交可能更差。','rebuy':'先恢复1手，随后确认120m重回EMA10再恢复第二手；第三手等待日线/关键位修复，总持仓不超过3手。','cancel':'仅回调但日线MA20保持、120m没有破坏，不以清仓作为默认。'},
          {'name':'向上突破','trigger':'30m站稳454，120m随后收复459并突破463.4且回踩守住。','action':'没有卖出则保持3手；已卖出则先评估踏空成本，不能无限等原买回价。','rebuy':'用新的回踩确认恢复已卖部分，计入高价买回和手续费；不增加到3手以上。','cancel':'突破后重新落回452以下，停止追价恢复。'}],
        'note':'这些为分层风险管理情景，尚无足够样本证明推荐动作胜率；表中历史固定ATR买回规则与此条件买回计划不是同一策略，不能混用其概率。'}}
    plan_file=folder/'three-day-plan.json'
    if plan_file.exists():
        reviewed_plan=json.loads(plan_file.read_text(encoding='utf-8'))
        if reviewed_plan.get('market_date')!=report_date:raise ValueError('Intraday action plan is stale')
        outcome['plan']=reviewed_plan['plan'];outcome['levels']=reviewed_plan['levels']
    elif report_date!='2026-09-22':
        raise ValueError('New trading day requires a newly reviewed three-day-plan.json; static seed prices cannot be reused')
    else:
        save(plan_file,{'market_date':report_date,'plan':outcome['plan'],'levels':levels})
    save(folder/'intraday-analysis.json',outcome);save(folder/'strategy-records.json',records)
    daily_snapshot=daily_root/'site-data/latest.json'
    snapshot=json.loads(daily_snapshot.read_text(encoding='utf-8'));snapshot['intraday']=safe(outcome)
    signature=hashlib.sha256(json.dumps({k:v for k,v in snapshot.items() if k!='prediction_id'},sort_keys=True).encode()).hexdigest()[:12]
    snapshot['prediction_id']=report_date+'-close-v2-'+signature
    save(daily_snapshot,snapshot)
    save(daily_root/'site-data/archive'/f'{snapshot["prediction_id"]}.json',snapshot)
    print(json.dumps(safe({'quality':quality,'state':outcome['state'],'stats':[{k:r[k] for k in ['id','n','wins','win_rate','wilson95','mean_delta_hkd','action_count']} for r in stats]}),ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--report-date',default='2026-09-22');p.add_argument('--collect-only',action='store_true');p.add_argument('--analyze-only',action='store_true');a=p.parse_args()
    folder=ROOT/'research-private'/f'tencent-intraday-{a.date}'
    if not a.analyze_only:collect_intraday(folder)
    if not a.collect_only:create_analysis(folder,a.report_date)

if __name__=='__main__':main()
