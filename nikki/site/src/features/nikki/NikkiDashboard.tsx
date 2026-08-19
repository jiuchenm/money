import type {AgentNote, MarketAsset, NikkiSnapshot} from './types';
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
  return text
    .replaceAll('RSP', '标普500等权指数')
    .replaceAll('IWM', '美股小盘股')
    .replaceAll('SPY', '标普500')
    .replaceAll('NDX', '纳斯达克100')
    .replaceAll('VIX', '美股恐慌指数')
    .replaceAll('HY OAS', '美国高收益债信用利差')
    .replaceAll('market_date 和 fetched_at', '对应交易日和更新时间');
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

export default function NikkiDashboard({snapshot, archived = false}: {snapshot: NikkiSnapshot; archived?: boolean}) {
  const fetched = new Date(snapshot.fetched_at).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false});
  const primaryNotes = ['china_markets', 'cross_asset'].flatMap((key) => snapshot.agent_notes?.[key] ? [[key, snapshot.agent_notes[key]] as const] : []);
  const secondaryNotes = Object.entries(snapshot.agent_notes || {}).filter(([key]) => !['china_markets', 'cross_asset'].includes(key));
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
        <div className={styles.sectionTitle}><h2>世界事件</h2><span>点击查看来源</span></div>
        {snapshot.world_events.length ? <ul className={styles.eventList}>{snapshot.world_events.slice(0, 8).map((event) => <li key={event.title + '-' + event.published_at}><a href={event.url} target="_blank" rel="noreferrer">{event.title}</a><span>{event.domain}</span></li>)}</ul> : <p className={styles.empty}>本次事件源被限流，行情数据仍有效。</p>}
      </div>
      <details className={styles.advancedData}><summary>查看进阶宏观数据</summary><p>这组数据适合判断美元流动性和信用压力，不作为港A单独买卖依据。</p>
        <div className={styles.macroList}>{snapshot.macro.map((item) => <div key={item.series}><span>{item.label}<small>{item.market_date}</small></span><strong>{formatValue(item.value)}</strong><span>{item.change > 0 ? '+' : ''}{item.change.toFixed(2)}</span></div>)}</div>
      </details>
    </section>
    <footer className={styles.dataFooter}><strong>证据边界</strong><p>{snapshot.data_quality.disclaimer}</p></footer>
  </main>;
}
