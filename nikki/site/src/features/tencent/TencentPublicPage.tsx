import {useMemo,useState} from 'react';
import styles from './tencent.module.css';

type Topic={id:string;title_zh:string;category:string;event_date?:string|null;published_at?:string|null;published_date?:string|null;source_name:string;url:string;summary_zh:string;tencent_link:string;direction:string;relevance:string;verification:string;heat_basis:string;market_timing:string};
export type PublicSnapshot={publication_mode:'public-original-research';report_date:string;prediction_id:string;research_cutoff:string;feature_cutoff:string;
 report:{headline:string;summary:string;confidence:string;news:string[];technical:string[];macro:string[];scenarios:{name:string;condition:string;range:string;invalidation:string}[];watch:string[];limitations:string[]};
 topics:Topic[];news_coverage:{unique_topics:number;technology_topics:number;verified:number;partial:number;window_start:string;window_end:string;note:string};
 model_evaluation:{horizon:number;target:string;oos_n:number;improvement_pct:number;coverage80:number;folds_won:number;fold_count:number}[];
 publication:{published_at:string;note:string};schedule:{note:string;timezone:string;start_time:string};};
const labels:Record<string,string>={return:'到期收益',upside:'最大上冲',downside:'最大下探',drawdown:'峰谷回撤'};
const relations:Record<string,string>={direct:'直接相关',indirect:'间接相关',background:'背景'};
const directions:Record<string,string>={up:'偏多',down:'偏空',mixed:'双向',neutral:'中性'};
const dateText=(v:string)=>new Date(v).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});

export default function TencentPublicPage({data}:{data:PublicSnapshot}){
 const [query,setQuery]=useState(''),[filter,setFilter]=useState('all');
 const topics=useMemo(()=>data.topics.filter(t=>(filter==='all'||filter===t.relevance)&&[t.title_zh,t.summary_zh,t.tencent_link].join(' ').toLowerCase().includes(query.toLowerCase())),[data,query,filter]);
 const r=data.report;
 return <main className={styles.page}>
  <header className={styles.header}><div><p className={styles.eyebrow}>TIDE RESEARCH · 0700.HK</p><h1>腾讯 · 每日研究</h1><p>{data.report_date} 交易日报告 · 消息 × 技术 × 宏观</p></div><nav><a href="#/">Nikki总览</a><a href="#/trends">市场趋势</a><a href="#/tencent" aria-current="page">腾讯</a></nav></header>
  <div className={styles.status}>最近报告 {data.report_date} · {data.schedule.note}<br/>发布 {dateText(data.publication.published_at)} · 新闻研究截至 {dateText(data.research_cutoff)}</div>
  <section className={styles.hero}><div><span>最近交易日预判</span><h2>{r.headline}</h2><p>{r.summary}</p><small>{r.confidence}</small></div><aside><span>本轮证据池</span><strong>{data.news_coverage.technology_topics}</strong><b>个科技话题</b><p>{data.news_coverage.verified}项核验<br/>{data.news_coverage.partial}项部分核验</p></aside></section>
  <div className={styles.pillars}>{[['消息面',r.news],['技术面',r.technical],['宏观数据面',r.macro]].map(([h,items])=><section key={h as string}><h2>{h}</h2><ul>{(items as string[]).map(v=><li key={v}>{v}</li>)}</ul></section>)}</div>
  <section className={styles.section}><h2>下一段走势怎样验证</h2><div className={styles.scenarios}>{r.scenarios.map(s=><article key={s.name}><h3>{s.name}</h3><strong>{s.range}</strong><p>{s.condition}</p><small>失效：{s.invalidation}</small></article>)}</div><p className={styles.note}>条件情景不是承诺收益或已校准胜率。信息截点：{dateText(data.feature_cutoff)}。</p></section>
  <section className={styles.section}><h2>公开模型的检验结果</h2><p>模型未证实稳定优势时，只保留实验评价；不把数值输出包装成确定性目标。</p><div className={styles.tableWrap}><table><thead><tr><th>窗口 / 目标</th><th>相对历史分布的损失改善</th><th>校准区间实际覆盖</th><th>样本数 / 胜出时间块</th></tr></thead><tbody>{data.model_evaluation.map(v=><tr key={v.horizon+v.target}><td>{v.horizon}日 · {labels[v.target]}</td><td>{v.improvement_pct==null?'—':v.improvement_pct.toFixed(1)+'%'}</td><td>{v.coverage80==null?'—':(v.coverage80*100).toFixed(1)+'%'}</td><td>{v.oos_n??0} / {v.folds_won??0} of {v.fold_count??0}</td></tr>)}</tbody></table></div><details><summary>查看研究限制</summary><ul>{r.limitations.map(v=><li key={v}>{v}</li>)}</ul></details></section>
  <section className={styles.section}><h2>科技话题与腾讯的传导关系</h2><p>{data.news_coverage.window_start} — {data.news_coverage.window_end} · {data.news_coverage.unique_topics}项科技及宏观话题</p><p className={styles.note}>{data.news_coverage.note}</p><div className={styles.filters}><input aria-label="搜索科技话题" placeholder="搜索产品、公司或传导关系" value={query} onChange={e=>setQuery(e.target.value)}/><select aria-label="筛选与腾讯的关系" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">全部关系</option><option value="direct">直接相关</option><option value="indirect">间接相关</option><option value="background">背景</option></select><span>{topics.length}项</span></div><div className={styles.topics}>{topics.map((t,i)=><details key={t.id}><summary><span className={styles.topicNumber}>{String(i+1).padStart(3,'0')}</span><span>{t.title_zh}<small>{t.category} · {(t.published_at||t.published_date||t.event_date||'日期待核验').slice(0,10)} · {t.market_timing==='after_close'?'收盘后信息':t.market_timing==='time_unknown'?'精确时间未知':'收盘前已知'}</small></span><em>{relations[t.relevance]} · {directions[t.direction]}</em></summary><p>{t.summary_zh}</p><p><b>传到腾讯：</b>{t.tencent_link}</p><p className={styles.note}>关注依据：{t.heat_basis} · {t.verification==='verified'?'已核验':'部分核验'}</p><a href={t.url} target="_blank" rel="noreferrer">来源 · {t.source_name}</a></details>)}</div></section>
  <section className={styles.section}><h2>下次报告要核对什么</h2><ul>{r.watch.map(v=><li key={v}>{v}</li>)}</ul><p className={styles.note}>{data.publication.note}</p><a href="https://finance.yahoo.com/quote/0700.HK/history/" target="_blank" rel="noreferrer">在原始行情平台查看腾讯K线</a></section>
  <footer className={styles.footer}>Tide · {data.prediction_id} · 研究失败时保留上一份成功报告与原日期。</footer>
 </main>;
}
