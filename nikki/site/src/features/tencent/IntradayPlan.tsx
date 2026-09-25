import {useState} from 'react';
import styles from './tencent.module.css';
type Stat={id:string;sell_lots:number;rebuy:boolean;triggered_rule:boolean;n:number;wins:number;losses:number;ties:number;win_rate:number;wilson95:number[];mean_delta_hkd:number;worst_delta_hkd:number;action_count:number;unrecovered_episodes:number;same_daily_state_n:number;same_daily_state_wins:number};
export type IntradayData={market_date:string;as_of:string;forecast_sessions:string[];
 position:{lots:number;shares_per_lot:number;shares:number;cost_hkd:number;last_daily_close:number;gross_price_pnl_hkd:number};
 quality:{continuous_bars:number;trading_days:number;aggregation_policy:string;auction_note:string;turnover_note:string;crosschecked_price_bars:number;price_conflicts:unknown[];median_volume_ratio_yahoo_to_eastmoney:number};
 state:{m30:Record<string,number>;h120:Record<string,number>;daily:Record<string,number>;sell_trigger_now:boolean};
 strategy_statistics:Stat[];protocol:Record<string,string>;fee_reference:{note:string;sources:string[]};
 plan:{headline:string;reason:string;note:string;days:{date:string;focus:string;default:string}[];actions:{name:string;trigger:string;action:string;rebuy:string;cancel:string}[]};};
const n=(x:number|null|undefined,d=1)=>x==null?'缺失':x.toLocaleString('zh-CN',{maximumFractionDigits:d});
const rate=(x:number)=>n(x*100)+'%';
const signed=(x:number)=>(x>=0?'+':'')+n(x,0);
export default function IntradayPlan({data}:{data:IntradayData}){
 const [sellPrice,setSellPrice]=useState(data.position.last_daily_close),[buyPrice,setBuyPrice]=useState(442),[lots,setLots]=useState(1);
 const [commission,setCommission]=useState(.03),[minimum,setMinimum]=useState(15),[slippage,setSlippage]=useState(.05);
 const shares=lots*100;
 const fee=(price:number)=>{const v=price*shares;return Math.ceil(v*.001)+v*.000127+Math.max(minimum,v*commission/100)+v*slippage/100};
 const cost=fee(sellPrice)+fee(buyPrice),gain=(sellPrice-buyPrice)*shares-cost;
 return <section className={styles.section}>
  <p className={styles.eyebrow}>未来3个港股通可交易日 · {data.forecast_sessions.join(' / ')}</p><h2>3手怎样减仓，再怎样买回</h2>
  <div className={styles.status}>以{data.market_date}最后完整行情预判；不是盘中监控。获胜＝三日期末净财富超过一直持有300股，已卖未买回的踏空也计入。</div>
  <section className={styles.hero}><div><span>当前技术结论</span><h2>{data.plan.headline}</h2><p>{data.plan.reason}</p><small>可靠行动获胜概率：证据不足。下方展示真实历史频率和宽区间，不把它当未来承诺。</small></div><aside><span>{data.position.lots}手 × {data.position.shares_per_lot}股</span><strong>{data.position.shares}股</strong><p>成本 HKD {n(data.position.cost_hkd,2)}<br/>港币价格浮盈 {signed(data.position.gross_price_pnl_hkd)}<br/>未扣费用及人民币汇兑</p></aside></section>
  <div className={styles.pillars}>{[['30分钟',data.state.m30,'短线触发'],['120分钟',data.state.h120,'方向确认'],['日线',data.state.daily,'背景与风险界限']].map(([name,s,role])=><section key={name as string}><h2>{name as string}</h2><p>{role as string}</p><p>收盘 {n((s as Record<string,number>).close,2)}<br/>MA5 {n((s as Record<string,number>).ma5,2)} · MA10 {n((s as Record<string,number>).ma10,2)}<br/>MA20 {n((s as Record<string,number>).ma20,2)}</p>{(s as Record<string,number>).ema10!=null&&<p>EMA10 {n((s as Record<string,number>).ema10,2)}</p>}</section>)}</div>
  <div className={styles.scenarios}>{data.plan.days.map(d=><article key={d.date}><h3>{d.date}</h3><p>{d.focus}</p><strong>{d.default}</strong></article>)}</div>
  <div className={styles.actionGrid}>{data.plan.actions.map(a=><article key={a.name}><h3>{a.name}</h3><p><b>触发：</b>{a.trigger}</p><p><b>数量：</b>{a.action}</p><p><b>买回：</b>{a.rebuy}</p><small>取消/失效：{a.cancel}</small></article>)}</div><p className={styles.note}>{data.plan.note}</p>
  <h3>历史上，这些动作赢过持有吗</h3><p>可用{data.quality.trading_days}个交易日、{data.quality.continuous_bars}根30分钟线，预热后仅13个不重叠三日窗口。卖出数量共享价格路径，不能当独立概率。分批买回实验采用卖价下方0.5/1/1.5倍前日ATR，并非上面的条件买回计划。</p>
  <div className={styles.tableWrap}><table><thead><tr><th>实验动作</th><th>胜/总窗口</th><th>历史胜率 / 95%参考区间</th><th>同日线背景胜/样本</th><th>触发 / 未买全</th><th>平均超额净财富</th><th>最差超额</th></tr></thead><tbody>{data.strategy_statistics.map(s=><tr key={s.id}><td>{s.triggered_rule?'等转弱':'次日开盘'}卖{s.sell_lots}手 · {s.rebuy?'阶梯买回':'保持现金'}</td><td>{s.wins}/{s.n}（持平{s.ties}）</td><td>{rate(s.win_rate)} / {rate(s.wilson95[0])}—{rate(s.wilson95[1])}</td><td>{s.same_daily_state_wins}/{s.same_daily_state_n}</td><td>{s.action_count} / {s.unrecovered_episodes}</td><td>{signed(s.mean_delta_hkd)} HKD</td><td>{signed(s.worst_delta_hkd)} HKD</td></tr>)}</tbody></table></div>
  <details><summary>怎样计算，哪些还不知道</summary><ul>{Object.entries(data.protocol).map(([k,v])=><li key={k}>{v}</li>)}</ul><p>{data.quality.aggregation_policy}</p><p>{data.quality.auction_note}</p><p>{data.quality.turnover_note}</p><p>交叉核验{data.quality.crosschecked_price_bars}根可比bar，收盘差异{data.quality.price_conflicts.length}根；两源成交量中位比{n(data.quality.median_volume_ratio_yahoo_to_eastmoney,3)}，统计范围不一致，不混算日内VWAP。</p></details>
  <h3>卖出后至少跌多少才值得买回</h3><div className={styles.calculator}>
   <label>卖价<input type="number" min="1" step="0.2" value={sellPrice} onChange={e=>setSellPrice(Math.max(1,Number(e.target.value)))}/></label>
   <label>买回价<input type="number" min="1" step="0.2" value={buyPrice} onChange={e=>setBuyPrice(Math.max(1,Number(e.target.value)))}/></label>
   <label>已卖手数<select value={lots} onChange={e=>setLots(Number(e.target.value))}>{[1,2,3].map(v=><option key={v}>{v}</option>)}</select></label>
   <label>佣金%/边<input type="number" min="0" step="0.01" value={commission} onChange={e=>setCommission(Math.max(0,Number(e.target.value)))}/></label>
   <label>最低佣金HKD<input type="number" min="0" value={minimum} onChange={e=>setMinimum(Math.max(0,Number(e.target.value)))}/></label>
   <label>滑点%/边<input type="number" min="0" step="0.01" value={slippage} onChange={e=>setSlippage(Math.max(0,Number(e.target.value)))}/></label>
  </div><p>假设来回成本约 <b>{n(cost,2)} HKD</b>；恢复同样{shares}股后净现金差约 <b>{signed(gain)} HKD</b>。约需至少{n(cost/shares,2)}港币/股价差覆盖该假设成本。</p><p className={styles.note}>{data.fee_reference.note} 这只是成交后的算术，不代表该买回价能成交，也未计人民币汇兑。回测固定使用每边0.20%压力成本，未随本计算器修改。</p><p>{data.fee_reference.sources.map((url,i)=><a key={url} href={url} target="_blank" rel="noreferrer">官方依据{i+1}　</a>)}</p>
 </section>;
}
