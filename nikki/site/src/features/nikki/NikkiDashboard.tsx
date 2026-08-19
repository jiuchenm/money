import type {AgentNote, MarketAsset, NikkiSnapshot, WorldEvent} from './types';
import Sparkline from './Sparkline';
import styles from './nikki.module.css';

const focusGroups = ['hong_kong', 'a_share'];
const focusSymbols: Record<string, string[]> = {
  hong_kong: ['^HSI', 'HSTECH.HK'],
  a_share: ['000001.SS', '000300.SS', '399006.SZ', '000852.SS'],
};
const assetNames: Record<string, string> = {
  '^HSI': '恒生指数',
  'HSTECH.HK': '恒生科技指数',
};
const externalAssets = [
  {group: 'rates_fx', symbol: 'CNY=X', name: '人民币汇率', impact: '人民币走强通常有利于港股外资情绪，也减轻A股外流压力。'},
  {group: 'nasdaq', symbol: '^NDX', name: '纳斯达克100', impact: '反映全球科技风险偏好，主要影响恒生科技与A股成长风格。'},
  {group: 'rates_fx', symbol: 'DX-Y.NYB', name: '美元指数', impact: '美元走强通常压制港股估值，也会收紧亚洲市场流动性。'},
  {group: 'risk', symbol: '^VIX', name: '美股恐慌指数', impact: '快速上升代表全球避险升温，港股往往先受外资风险控制影响。'},
  {group: 'metals', symbol: 'GC=F', name: '黄金', impact: '用于观察避险和货币信用压力，不直接等同于股市利空。'},
  {group: 'energy', symbol: 'CL=F', name: 'WTI原油', impact: '影响输入性通胀、运输成本和中资能源股盈利预期。'},
];

const noteNames: Record<string, string> = {china_markets: '港A市场', cross_asset: '跨市场传导', us_macro: '美股环境', metals_energy: '商品环境'};

function friendlyText(text: string) {
  const terms: Array<[string, string]> = [
    ['market_date 和 fetched_at', '对应交易日和更新时间'],
    ['HY OAS', '美国高收益债信用利差'], ['SOXX', '美股半导体指数基金'],
    ['RSP', '标普500等权指数'], ['IWM', '美股小盘股指数基金'],
    ['SPY', '标普500指数基金'], ['NDX', '纳斯达克100'], ['XLK', '美股科技板块'],
    ['VIX', '美股恐慌指数'], ['HYG', '美国高收益债基金'], ['TLT', '美国长期国债基金'],
    ['XLP', '美股必需消费板块'], ['XLU', '美股公用事业板块'], ['XLE', '美股能源板块'],
    ['GLD', '黄金基金'], ['10Y', '美国10年期国债收益率'], ['risk-off', '避险模式'],
  ];
  return terms.reduce((result, [term, replacement]) => result.replaceAll(term, replacement), text);
}

type MacroItem = NikkiSnapshot['macro'][number];
type MacroView = {name: string; measure: string; reading: string; impact: string; tone: 'support' | 'neutral' | 'pressure'};

function macroView(item: MacroItem): MacroView {
  const move = `${item.change > 0 ? '上升' : item.change < 0 ? '下降' : '持平'} ${Math.abs(item.change).toFixed(2)} 个百分点`;
  switch (item.series) {
    case 'BAMLH0A0HYM2':
      return {name: '美国高收益债信用利差', measure: '衡量低评级企业融资压力。利差急升常代表避险和信用风险扩散。', reading: `当前 ${item.value.toFixed(2)}%，较前值${move}。绝对水平仍低，系统性信用压力有限。`, impact: item.change > 0 ? '轻微压制港股风险偏好，但暂未构成信用危机信号。' : '信用压力没有恶化，对港A风险偏好偏中性。', tone: item.change > 0 ? 'pressure' : 'neutral'};
    case 'DFF':
      return {name: '美国有效联邦基金利率', measure: '反映美元政策利率环境，也是全球资金成本的重要基准。', reading: `当前 ${item.value.toFixed(2)}%，较前值${move}。日度不变不是新的政策信号。`, impact: '高利率环境仍压制港股成长股估值，但单日持平对A股没有新增方向。', tone: 'neutral'};
    case 'DFII10':
      return {name: '美国10年期实际利率', measure: '剔除通胀预期后的长期实际折现率，影响黄金和成长股估值。', reading: `当前 ${item.value.toFixed(2)}%，较前值${move}。`, impact: item.change > 0 ? '实际利率上升，提高估值折现压力，通常不利于恒生科技和A股高估值成长。' : '实际利率回落，边际有利于港股科技和A股成长估值。', tone: item.change > 0 ? 'pressure' : item.change < 0 ? 'support' : 'neutral'};
    case 'T10Y2Y':
      return {name: '美国10年与2年国债利差', measure: '观察收益率曲线斜率。负值倒挂常对应经济衰退担忧，转正不等于经济必然走强。', reading: `当前 ${item.value.toFixed(2)}%，较前值${move}。曲线仍为正。`, impact: '单日小幅变窄证据较弱，对港A暂按中性处理。', tone: 'neutral'};
    default:
      return {name: item.label, measure: '用于观察海外流动性、增长或信用环境。', reading: `当前 ${item.value}，较前值${move}。`, impact: '暂未建立可靠的港A传导规则，只作为观察项。', tone: 'neutral'};
  }
}

function isTimelyProcessedEvent(event: WorldEvent, reportDate: string) {
  if (!event.chinese_summary || !event.hk_a_impact || !event.published_at) return false;
  const published = new Date(event.published_at).getTime();
  const reportEnd = new Date(`${reportDate}T23:59:59+08:00`).getTime();
  return Number.isFinite(published) && published <= reportEnd && published >= reportEnd - 72 * 60 * 60 * 1000;
}

function formatValue(value: number) {
  return new Intl.NumberFormat('zh-CN', {maximumFractionDigits: value >= 100 ? 1 : 3}).format(value);
}

function Change({value}: {value: number | null}) {
  if (value == null) return <span className={styles.muted}>--</span>;
  const className = value > 0 ? styles.positive : value < 0 ? styles.negative : styles.muted;
  return <span className={className}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>;
}

function CoreAsset({asset}: {asset: MarketAsset}) {
  const trend = asset.above_50d == null ? '趋势待确认' : asset.above_50d ? '中期趋势向上' : '中期趋势承压';
  return <article className={styles.coreAsset}>
    <div className={styles.coreAssetHead}>
      <div><h3>{assetNames[asset.symbol] || asset.name}</h3><span>{asset.market_date}</span></div>
      <div className={styles.coreQuote}><strong>{formatValue(asset.value)}</strong><Change value={asset.change_1d} /></div>
    </div>
    <Sparkline points={asset.sparkline} positive={asset.change_20d != null && asset.change_20d >= 0} />
    <div className={styles.periods}>
      <span>近5日 <Change value={asset.change_5d} /></span>
      <span>近20日 <Change value={asset.change_20d} /></span>
      <span>距一年高点 <Change value={asset.drawdown_1y} /></span>
    </div>
    <div className={asset.above_50d ? styles.trendUp : styles.trendDown}>{trend}</div>
    <details className={styles.assetDetails}><summary>查看代码与数据来源</summary><p>{asset.symbol} · {asset.source}</p></details>
  </article>;
}

function ChinaSection({snapshot, groupId}: {snapshot: NikkiSnapshot; groupId: string}) {
  const group = snapshot.groups[groupId];
  if (!group) return null;
  return <section className={styles.focusSection} id={groupId}>
    <div className={styles.sectionTitle}><h2>{group.title}</h2><span>{group.status === 'ok' ? '收盘数据完整' : '部分数据'}</span></div>
    <div className={styles.coreGrid}>{focusSymbols[groupId].flatMap((symbol) => group.assets[symbol] ? [<CoreAsset key={symbol} asset={group.assets[symbol]} />] : [])}</div>
  </section>;
}

function DecisionBrief({note, label}: {note: AgentNote; label: string}) {
  return <article className={styles.decisionBrief}>
    <span>{label}</span><h3>{friendlyText(note.headline)}</h3>{note.forces[0] && <p>{friendlyText(note.forces[0])}</p>}
    <details><summary>展开依据与观察条件</summary>
      <h4>主要力量</h4><ul>{note.forces.map((item) => <li key={item}>{friendlyText(item)}</li>)}</ul>
      <h4>市场分歧</h4><ul>{note.divergences.map((item) => <li key={item}>{friendlyText(item)}</li>)}</ul>
      <h4>后续触发</h4><ul>{note.triggers.map((item) => <li key={item}>{friendlyText(item)}</li>)}</ul>
    </details>
  </article>;
}

function ExternalCard({asset, name, impact}: {asset: MarketAsset; name: string; impact: string}) {
  return <article className={styles.externalCard}>
    <div><h3>{name}</h3><span>{asset.market_date}</span></div>
    <div className={styles.externalQuote}><strong>{formatValue(asset.value)}</strong><Change value={asset.change_1d} /></div>
    <p>{impact}</p>
    <details><summary>近20日与代码</summary><p>近20日 <Change value={asset.change_20d} /> · {asset.symbol}</p></details>
  </article>;
}

function MacroCard({item}: {item: MacroItem}) {
  const view = macroView(item);
  return <article className={styles.macroCard}>
    <div className={styles.macroHead}><h3>{view.name}</h3><span className={styles[view.tone]}>{view.tone === 'support' ? '边际支持港A' : view.tone === 'pressure' ? '边际压制港A' : '对港A中性'}</span></div>
    <p>{view.measure}</p><strong>{view.reading}</strong><p>{view.impact}</p>
    <details><summary>查看数据口径与来源</summary><p>{item.series} · 数据日 {item.market_date} · {item.source}。FRED 日度数据可能滞后，不代表实时盘中变化。</p></details>
  </article>;
}

function EventCard({event}: {event: WorldEvent}) {
  const published = new Date(event.published_at || '').toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false});
  return <article className={styles.eventCard}>
    <div className={styles.eventHead}><span>{event.source_tier === 'primary' ? '一手来源' : '可靠媒体线索'}</span><time>{published}</time></div>
    <h3>{event.chinese_summary}</h3><p><strong>对港A：</strong>{event.hk_a_impact}</p>
    {event.affected_assets?.length ? <p className={styles.affected}>主要影响：{event.affected_assets.join('、')}</p> : null}
    <details><summary>查看原文与证据状态</summary><p>{event.title} · {event.domain || event.source}</p>{event.url && <a href={event.url} target="_blank" rel="noreferrer">打开原始来源</a>}</details>
  </article>;
}

export default function NikkiDashboard({snapshot, archived = false}: {snapshot: NikkiSnapshot; archived?: boolean}) {
  const fetched = new Date(snapshot.fetched_at).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false});
  const primaryNotes = ['china_markets', 'cross_asset'].flatMap((key) => snapshot.agent_notes?.[key] ? [[key, snapshot.agent_notes[key]] as const] : []);
  const secondaryNotes = Object.entries(snapshot.agent_notes || {}).filter(([key]) => !['china_markets', 'cross_asset'].includes(key));
  const processedEvents = snapshot.world_events.filter((event) => isTimelyProcessedEvent(event, snapshot.report_date));
  return <main className={styles.page}>
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>NIKKI · 港A市场雷达</p><h1>{archived ? snapshot.report_date + ' 市场档案' : '港股与A股今日总览'}</h1><p className={styles.subhead}>更新时间 {fetched} · {snapshot.data_quality.status === 'ok' ? '主要数据源正常' : '部分来源降级'}</p></div>
      <nav className={styles.tabs} aria-label="Nikki 页面"><a href="#/">最新</a><a href="#/trends">港A趋势</a><a href="#/archive">历史</a></nav>
    </header>
    <div className={styles.phaseNote}>{friendlyText(snapshot.market_phase_note)}</div>

    {primaryNotes.length > 0 && <section className={styles.decisionSection}>
      <div className={styles.sectionTitle}><h2>今天先看什么</h2><span>Agent 综合判断</span></div>
      <div className={styles.decisionGrid}>{primaryNotes.map(([key, note]) => <DecisionBrief key={key} note={note} label={noteNames[key]} />)}</div>
    </section>}

    <nav className={styles.marketRail} aria-label="港A市场快速导航"><a href="#hong_kong">港股</a><a href="#a_share">A股</a><a href="#external">外部影响</a><a href="#events">世界事件</a></nav>
    <div className={styles.focusGrid}>{focusGroups.map((id) => <ChinaSection key={id} snapshot={snapshot} groupId={id} />)}</div>

    <section className={styles.externalSection} id="external">
      <div className={styles.sectionTitle}><h2>影响港A的外部变量</h2><span>只保留六项</span></div>
      <div className={styles.externalGrid}>{externalAssets.map((item) => {
        const asset = snapshot.groups[item.group]?.assets[item.symbol];
        return asset ? <ExternalCard key={item.symbol} asset={asset} name={item.name} impact={item.impact} /> : null;
      })}</div>
    </section>

    <section className={styles.signalSection}>
      <div className={styles.sectionTitle}><h2>外部风险温度</h2><span>不是买卖信号</span></div>
      <div className={styles.signalBand}>{snapshot.signals.map((signal) => <article key={signal.label} className={styles.signal + ' ' + styles[signal.level]}>
        <span>{signal.level === 'risk' ? '风险升高' : signal.level === 'watch' ? '需要观察' : '暂时正常'}</span><strong>{friendlyText(signal.label)}</strong><p>{friendlyText(signal.detail)}</p>
      </article>)}</div>
    </section>

    {secondaryNotes.length > 0 && <details className={styles.secondaryAnalysis}><summary>查看美股与商品的补充分析</summary>
      <div className={styles.decisionGrid}>{secondaryNotes.map(([key, note]) => <DecisionBrief key={key} note={note} label={noteNames[key] || key} />)}</div>
    </details>}

    <section className={styles.bottomGrid} id="events">
      <div className={styles.plainSection}>
        <div className={styles.sectionTitle}><h2>世界事件如何影响港A</h2><span>只展示72小时内可靠证据</span></div>
        {processedEvents.length ? <div className={styles.eventList}>{processedEvents.map((event) => <EventCard key={event.title + '-' + event.published_at} event={event} />)}</div> : <p className={styles.empty}>今日没有足够可靠的事件证据，不能用旧闻解释当日行情。</p>}
      </div>
      <div className={styles.advancedData}><div className={styles.sectionTitle}><h2>海外宏观数据怎么读</h2><span>已换算为港A传导</span></div><p>这组数据用于判断美元流动性、估值和信用压力，不能单独作为买卖信号。</p>
        <div className={styles.macroList}>{snapshot.macro.map((item) => <MacroCard key={item.series} item={item} />)}</div>
      </div>
    </section>
    <footer className={styles.dataFooter}><strong>证据边界</strong><p>{snapshot.data_quality.disclaimer}</p></footer>
  </main>;
}
