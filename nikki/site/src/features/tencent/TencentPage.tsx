import {useEffect, useMemo, useState} from 'react';
import styles from './tencent.module.css';
import TencentPublicPage from './TencentPublicPage';
import type {PublicSnapshot} from './TencentPublicPage';

type Bar = {date:string;close:number|null;open:number|null;high_observed:number|null;low_observed:number|null;volume:number;turnover:number;ma5?:number|null;ma10?:number|null;ma20?:number|null;partial?:boolean};
type Topic = {id:string;title_zh:string;category:string;published_at:string|null;published_date?:string|null;event_date?:string|null;source_name:string;url:string;summary_zh:string;tencent_link:string;direction:string;relevance:string;verification:string;heat_basis:string;market_timing:string};
type Scenario = {name:string;condition:string;range:string;invalidation:string};
type TargetResult={status:string;oos_n?:number;improvement_pct?:number;coverage80?:number;folds_won?:number;fold_count?:number;current?:{lightgbm:number[];calibrated_interval:number[];empirical:number[];training_n:number;calibration_n:number}};
type Snapshot={report_date:string;generated_at:string;feature_cutoff:string;research_cutoff:string;publication_mode:string;
 technical:{close:number;open:number;high:number;low:number;change_1d:number;volume:number;turnover:number;ma:Record<string,number>;atr14:number;rsi14:number;volume_ratio:number;gap_pct:number;range_position:number;return_5d:number;return_20d:number;drawdown_250:number};
 assets:{symbol:string;name:string;date:string;value:number;change_1d:number;change_5d:number;source_url:string;note:string}[];
 macro:{name:string;value:number;date:string;source_url:string;note:string}[];
 quality:{price_conflicts:unknown[];resolved_conflict_count:number;daily_count:number;full_count:number;missing_sessions:string[];unexpected_sessions:string[];volume_difference_latest:number};
 forecasts:{horizon:number;targets:Record<string,TargetResult>}[];
 analogs:{horizon:number;n:number;note:string;quantiles:Record<string,number[]>;positive_rate:number;first_up_5_lower:number;first_up_5_upper:number}[];
 chart?:{daily:Bar[];weekly:Bar[];monthly:Bar[]};
 topics:Topic[];news_coverage:{unique_topics:number;window_start:string;window_end:string;verified:number;partial:number;note:string};
 report:{headline:string;summary:string;confidence:string;news:string[];technical:string[];macro:string[];scenarios:Scenario[];watch:string[];limitations:string[]};
 model_protocol:{feature_count:number;validation:string;limitations:string[]};};

const pct=(n:number|undefined,d=1)=>n==null?'—':(n>=0?'+':'')+n.toFixed(d)+'%';
const num=(n:number|null|undefined,d=2)=>n==null?'—':n.toLocaleString('zh-CN',{maximumFractionDigits:d});
const qrange=(q:number[]|undefined,signed=true)=>q?q.map(v=>signed?pct(v*100):num(v*100,1)+'%').join(' / '):'样本不足';
const label:Record<string,string>={return:'到期收益',upside:'最大上冲',downside:'最大下探',drawdown:'峰谷回撤'};
const relevance:Record<string,string>={direct:'直接相关',indirect:'间接相关',background:'背景'};
const direction:Record<string,string>={up:'偏多',down:'偏空',mixed:'双向',neutral:'中性'};

function PriceChart({bars}:{bars:Bar[]}) {
  const shown=bars.slice(-110).filter(b=>b.close!=null);
  const [hover,setHover]=useState<number|null>(null);
  const width=1050,height=320,top=24,bottom=250;
  if(!shown.length)return <p>没有可展示的行情。</p>;
  const values=shown.flatMap(b=>[b.high_observed,b.low_observed,b.ma5,b.ma10,b.ma20]).filter((v):v is number=>v!=null);
  const low=Math.min(...values)*.985,high=Math.max(...values)*1.015;
  const x=(i:number)=>45+i*(width-65)/Math.max(1,shown.length-1);
  const y=(v:number)=>top+(high-v)/(high-low)*(bottom-top);
  const volMax=Math.max(...shown.map(b=>b.volume));
  const selected=shown[hover??shown.length-1];
  const series=(key:'ma5'|'ma10'|'ma20')=>shown.map((b,i)=>b[key]!=null?(i===0||shown[i-1][key]==null?'M':'L')+x(i)+','+y(b[key]!):'').join(' ');
  return <><div className={styles.chartInfo}>{selected.date} {selected.partial?'· 未完成周期':''}　开 {num(selected.open)}　高 {num(selected.high_observed)}　低 {num(selected.low_observed)}　收 {num(selected.close)}　成交额 {num(selected.turnover/1e8)} 亿</div>
    <svg className={styles.chart} viewBox={'0 0 '+width+' '+height} role="img" aria-label="腾讯K线、MA5、MA10、MA20和成交量" onMouseLeave={()=>setHover(null)}>
      {[0,1,2,3,4].map(i=><g key={i}><line x1="45" x2="1040" y1={top+i*(bottom-top)/4} y2={top+i*(bottom-top)/4} stroke="#283744"/><text x="0" y={top+i*(bottom-top)/4+4} fill="#b2c1cd" fontSize="11">{num(high-i*(high-low)/4,0)}</text></g>)}
      {shown.map((b,i)=>{const up=b.close!>=b.open!;return <g key={b.date} onMouseEnter={()=>setHover(i)}><line x1={x(i)} x2={x(i)} y1={y(b.high_observed!)} y2={y(b.low_observed!)} stroke={up?'#ff8d92':'#53d8ad'}/><rect x={x(i)-2.7} width="5.4" y={Math.min(y(b.close!),y(b.open!))} height={Math.max(1,Math.abs(y(b.close!)-y(b.open!)))} fill={up?'#ff8d92':'#53d8ad'}/><rect x={x(i)-3} width="6" y={307-b.volume/volMax*38} height={b.volume/volMax*38} fill={up?'#914f59':'#287e67'}/><rect x={x(i)-5} width="10" y="20" height="290" fill="transparent"/></g>})}
      <path d={series('ma5')} stroke="#f4ce74" fill="none" strokeWidth="1.3"/><path d={series('ma10')} stroke="#91b9ff" fill="none" strokeWidth="1.3"/><path d={series('ma20')} stroke="#db9bff" fill="none" strokeWidth="1.3"/>
      {hover!=null&&<line x1={x(hover)} x2={x(hover)} y1="20" y2="310" stroke="#bdc7cf" strokeDasharray="4 4"/>}
      <text x="45" y="320" fill="#b2c1cd" fontSize="11">{shown[0].date}</text><text x="965" y="320" fill="#b2c1cd" fontSize="11">{shown[shown.length-1].date}</text>
    </svg><div className={styles.legend}><span>MA5</span><span>MA10</span><span>MA20</span><small>红涨绿跌 · 日内高低顺序未知 · 冲突经第三源核对</small></div></>;
}

export default function TencentPage(){
  const [payload,setData]=useState<Snapshot|PublicSnapshot|null>(null),[error,setError]=useState('');
  const [period,setPeriod]=useState<'daily'|'weekly'|'monthly'>('daily');
  const [query,setQuery]=useState(''),[filter,setFilter]=useState('all');
  useEffect(()=>{document.title='腾讯波段观察 · Tide';const controller=new AbortController();fetch(import.meta.env.BASE_URL+'data/tencent/latest.json',{signal:controller.signal,cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('尚未生成腾讯报告');return r.json()}).then(setData).catch(e=>{if(e.name!=='AbortError')setError(String(e.message))});return()=>{controller.abort();document.title='Nikki 市场总览'}},[]);
  const topics=useMemo(()=>payload?.topics.filter(t=>(filter==='all'||t.relevance===filter)&&[t.title_zh,t.category,t.summary_zh,t.tencent_link].join(' ').toLowerCase().includes(query.toLowerCase()))??[],[payload,filter,query]);
  if(error)return <main className={styles.page}><h1>腾讯波段观察</h1><p>{error}</p><a href="#/">返回 Nikki</a></main>;
  if(!payload)return <main className={styles.page}><h1>正在读取腾讯报告…</h1></main>;
  if(payload.publication_mode==='public-original-research')return <TencentPublicPage data={payload as PublicSnapshot}/>;
  const data=payload as Snapshot;
  const t=data.technical,r=data.report;
  const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Hong_Kong'});
  const stale=today>data.report_date;
  return <main className={styles.page}>
    <header className={styles.header}><div><p className={styles.eyebrow}>TIDE RESEARCH · 0700.HK</p><h1>腾讯 · 波段观察</h1><p>{data.report_date} 收盘研究版 · 消息 × 技术 × 宏观</p></div><nav><a href="#/">Nikki总览</a><a href="#/archive">市场档案</a><a href="#/tencent" aria-current="page">腾讯</a></nav></header>
    <div className={styles.status}>{stale?'历史快照：请检查数据日期':'今日研究快照'} · 行情特征截至 {data.feature_cutoff} · 本版为实验研究，预测优势尚未确认</div>
    <section className={styles.hero}><div><span>今日预判</span><h2>{r.headline}</h2><p>{r.summary}</p><small>{r.confidence}</small></div><aside><span>腾讯港币收盘</span><strong>{num(t.close)}</strong><b className={t.change_1d>=0?styles.up:styles.down}>{pct(t.change_1d,2)}</b><p>成交额 {num(t.turnover/1e8)} 亿<br/>前20日均量的 {num(t.volume_ratio)} 倍</p></aside></section>
    <div className={styles.metrics}>{[['MA5',t.ma['5']],['MA10',t.ma['10']],['MA20',t.ma['20']],['MA60',t.ma['60']],['RSI14',t.rsi14],['ATR14',t.atr14]].map(([name,value])=><div key={name as string}><span>{name}</span><strong>{num(value as number)}</strong></div>)}</div>
    <section className={styles.section}><div className={styles.sectionHead}><h2>先看量价处在什么位置</h2><div className={styles.controls}>{(['daily','weekly','monthly'] as const).map((p,i)=><button key={p} className={period===p?styles.active:''} onClick={()=>setPeriod(p)}>{['日线','周线','月线'][i]}</button>)}</div></div>
      {data.chart?<PriceChart bars={data.chart[period]}/>:<p>完整行情仅保留在本地研究视图，公开产物未包含原始历史库。</p>}
      <div className={styles.smallGrid}><span>5日 {pct(t.return_5d)}</span><span>20日 {pct(t.return_20d)}</span><span>距250日高点 {pct(t.drawdown_250)}</span><span>跳空 {pct(t.gap_pct)}</span></div>
    </section>
    <div className={styles.pillars}>{[['消息面',r.news],['技术面',r.technical],['宏观数据面',r.macro]].map(([heading,items])=><section key={heading as string}><h2>{heading}</h2><ul>{(items as string[]).map(text=><li key={text}>{text}</li>)}</ul></section>)}</div>
    <section className={styles.section}><h2>用条件判断下一段走势</h2><div className={styles.scenarios}>{r.scenarios.map(s=><article key={s.name}><h3>{s.name}</h3><strong>{s.range}</strong><p>{s.condition}</p><small>失效：{s.invalidation}</small></article>)}</div><p className={styles.note}>这些是证据支持的观察情景，不是已校准胜率或精确买卖点。价格范围必须与触发条件同时阅读。</p></section>
    <section className={styles.section}><h2>算法是否真的比历史分布更准</h2><p>LightGBM · {data.model_protocol.feature_count} 项状态输入 · 5/10/20日 · q10/q50/q90。消息面只进入本日研判，未伪造历史新闻特征。</p>
      <div className={styles.tableWrap}><table><thead><tr><th>窗口/目标</th><th>模型原始 q10 / q50 / q90</th><th>校准80%下界 / 上界</th><th>历史分布对照</th><th>原始分位数样本外改善</th><th>校准区间实测覆盖</th></tr></thead><tbody>{data.forecasts.flatMap(h=>Object.entries(h.targets).map(([key,v])=><tr key={h.horizon+key}><td>{h.horizon}日 · {label[key]}</td><td>{qrange(v.current?.lightgbm,key==="return")}</td><td>{qrange(v.current?.calibrated_interval,key==="return")}</td><td>{qrange(v.current?.empirical,key==="return")}</td><td>{pct(v.improvement_pct)} · {v.folds_won??0}/{v.fold_count??0}窗口胜出</td><td>{v.coverage80==null?'—':num(v.coverage80*100,1)+'%'} · n={v.oos_n??0}</td></tr>))}</tbody></table></div>
      <details><summary>读懂区间、验证和局限</summary><p>{data.model_protocol.validation}</p><p>q90上冲不是90%概率能涨到；上下分位数不是联合价格路径。重叠的20日标签不等于独立样本。最大回撤采用收盘路径，不含无法判定的日内高低点顺序。</p><ul>{[...data.model_protocol.limitations,...r.limitations].map(v=><li key={v}>{v}</li>)}</ul></details>
    </section>
    <section className={styles.section}><h2>腾讯相似状态曾怎样走</h2><p className={styles.note}>仅作历史描述，尚未证明能预测今天。按窗口间隔取样仍不等于样本完全独立；量价状态相似不代表消息背景相同。</p><div className={styles.tableWrap}><table><thead><tr><th>窗口 / 样本数</th><th>上冲中位数</th><th>下探中位数</th><th>回撤中位数</th><th>到期上涨频率</th><th>先+5%而非-5%频率界限</th></tr></thead><tbody>{data.analogs.map(a=><tr key={a.horizon}><td>{a.horizon}日 / {a.n}</td><td>{num(a.quantiles.upside[1]*100,1)}%</td><td>{num(a.quantiles.downside[1]*100,1)}%</td><td>{num(a.quantiles.drawdown[1]*100,1)}%</td><td>{num(a.positive_rate*100,1)}%</td><td>{num(a.first_up_5_lower*100,1)}%—{num(a.first_up_5_upper*100,1)}%</td></tr>)}</tbody></table></div></section>
    <section className={styles.section}><h2>核对美股与全球资产</h2><div className={styles.assetGrid}>{data.assets.map(a=><a key={a.symbol} href={a.source_url} target="_blank" rel="noreferrer"><span>{a.name}</span><strong>{num(a.value)}</strong><b className={a.change_1d>=0?styles.up:styles.down}>{pct(a.change_1d)}</b><small>{a.date} · 5日 {pct(a.change_5d)}</small></a>)}</div>{data.macro.length>0&&<div className={styles.assetGrid}>{data.macro.map(a=><a key={a.name} href={a.source_url} target="_blank" rel="noreferrer"><span>{a.name}</span><strong>{num(a.value)}</strong><small>{a.date} · {a.note}</small></a>)}</div>}</section>
    <section className={styles.section}><h2>逐条检查科技话题与腾讯的关系</h2><p>本轮 {data.news_coverage.unique_topics} 个独立话题 · {data.news_coverage.window_start} 至 {data.news_coverage.window_end} · {data.news_coverage.verified} 项核验 / {data.news_coverage.partial} 项部分核验</p><p className={styles.note}>{data.news_coverage.note}</p>
      <div className={styles.filters}><input aria-label="搜索科技话题" value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索公司、产品、事件或传导关系"/><select aria-label="筛选与腾讯的关系" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">全部关系</option><option value="direct">直接相关</option><option value="indirect">间接相关</option><option value="background">背景</option></select><span>{topics.length} 项</span></div>
      <div className={styles.topics}>{topics.map((topic,i)=><details key={topic.id}><summary><span className={styles.topicNumber}>{String(i+1).padStart(3,'0')}</span><span>{topic.title_zh}<small>{topic.category} · 发布 {(topic.published_at||topic.published_date||'日期待核验').slice(0,10)} · {topic.market_timing==='after_close'?'收盘后信息':topic.market_timing==='time_unknown'?'精确时点未知':'收盘前已知'}</small></span><em>{relevance[topic.relevance]||topic.relevance} · {direction[topic.direction]||topic.direction}</em></summary><p>{topic.summary_zh}</p><p><b>传到腾讯：</b>{topic.tencent_link}</p><p className={styles.note}>发生日：{topic.event_date||'待核验'} · 关注依据：{topic.heat_basis} · 证据：{topic.verification}</p><a href={topic.url} target="_blank" rel="noreferrer">查看来源 · {topic.source_name}</a></details>)}</div>
    </section>
    <section className={styles.section}><h2>下一次更新要验证什么</h2><ul>{r.watch.map(v=><li key={v}>{v}</li>)}</ul><details><summary>数据质量与更新记录</summary><p>三年日线 {data.quality.daily_count} 条；可比历史 {data.quality.full_count} 条；发现收盘冲突 {data.quality.price_conflicts.length} 日，其中 {data.quality.resolved_conflict_count} 日有第三源支持裁决；最后日成交量源差 {num(data.quality.volume_difference_latest,0)} 股。</p><p>生成时间 {data.generated_at}；消息研究截点 {data.research_cutoff}。当前为本次执行生成的快照，自动调度与推送状态以运行记录为准。</p></details></section>
    <footer className={styles.footer}>Tide · 原始数据与个人持仓留在私有研究目录。每份预测保留当时的信息集，后续结果用于检验。</footer>
  </main>;
}
