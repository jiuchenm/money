import type {NikkiSnapshot, MarketAsset} from './types';
import Sparkline from './Sparkline';
import styles from './nikki.module.css';

const order = ['nasdaq', 'rates_fx', 'metals', 'energy', 'risk', 'hong_kong', 'a_share', 'rotation'];

function formatValue(value: number) {
  return new Intl.NumberFormat('zh-CN', {maximumFractionDigits: value >= 100 ? 1 : 3}).format(value);
}

function Change({value}: {value: number | null}) {
  if (value == null) return <span className={styles.muted}>--</span>;
  const className = value > 0 ? styles.positive : value < 0 ? styles.negative : styles.muted;
  return <span className={className}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>;
}

function AssetRow({asset}: {asset: MarketAsset}) {
  return (
    <div className={styles.assetRow}>
      <div className={styles.assetIdentity}>
        <strong>{asset.name}</strong>
        <span>{asset.symbol} · {asset.market_date}</span>
      </div>
      <div className={styles.assetValue}>
        <strong>{formatValue(asset.value)}</strong>
        <Change value={asset.change_1d} />
      </div>
      <Sparkline points={asset.sparkline} positive={asset.change_20d != null && asset.change_20d >= 0} />
      <div className={styles.assetWindows}>
        <span>5D <Change value={asset.change_5d} /></span>
        <span>20D <Change value={asset.change_20d} /></span>
        <span>1Y DD <Change value={asset.drawdown_1y} /></span>
      </div>
      <div className={styles.trendFlags} aria-label="趋势状态">
        <span className={asset.above_50d ? styles.flagOn : styles.flagOff}>50D</span>
        <span className={asset.above_200d ? styles.flagOn : styles.flagOff}>200D</span>
      </div>
    </div>
  );
}

function GroupSection({snapshot, groupId}: {snapshot: NikkiSnapshot; groupId: string}) {
  const group = snapshot.groups[groupId];
  if (!group) return null;
  return (
    <section className={styles.marketSection} id={groupId}>
      <div className={styles.sectionTitle}>
        <h2>{group.title}</h2>
        <span>{group.status === 'ok' ? '数据完整' : '部分数据'}</span>
      </div>
      <div className={styles.assetList}>
        {Object.values(group.assets).map((asset) => <AssetRow key={asset.symbol} asset={asset} />)}
      </div>
    </section>
  );
}

function AgentBriefs({snapshot}: {snapshot: NikkiSnapshot}) {
  const notes = Object.entries(snapshot.agent_notes || {});
  if (!notes.length) return null;
  return (
    <section className={styles.briefSection}>
      <div className={styles.sectionTitle}><h2>独立 Agent 判断</h2><span>{notes.length} 个板块</span></div>
      <div className={styles.briefGrid}>
        {notes.map(([key, note]) => <article key={key} className={styles.brief}>
          <span>{key.replaceAll('_', ' ').toUpperCase()}</span>
          <h3>{note.headline}</h3>
          <p>{note.forces[0]}</p>
          <details><summary>驱动力、分歧与触发</summary>
            <strong>驱动力</strong><ul>{note.forces.map((item) => <li key={item}>{item}</li>)}</ul>
            <strong>分歧</strong><ul>{note.divergences.map((item) => <li key={item}>{item}</li>)}</ul>
            <strong>触发</strong><ul>{note.triggers.map((item) => <li key={item}>{item}</li>)}</ul>
          </details>
        </article>)}
      </div>
    </section>
  );
}

export default function NikkiDashboard({snapshot, archived = false}: {snapshot: NikkiSnapshot; archived?: boolean}) {
  const fetched = new Date(snapshot.fetched_at).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false});
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>NIKKI · DAILY MARKET TAPE</p>
          <h1>{archived ? snapshot.report_date + ' 市场档案' : '今日市场总览'}</h1>
          <p className={styles.subhead}>数据时间 {fetched} · {snapshot.data_quality.status === 'ok' ? '全部来源正常' : '部分来源降级'}</p>
        </div>
        <nav className={styles.tabs} aria-label="Nikki 页面">
          <a href="#/">最新</a>
          <a href="#/trends">趋势</a>
          <a href="#/archive">归档</a>
        </nav>
      </header>

      <div className={styles.phaseNote}>{snapshot.market_phase_note}</div>

      <section className={styles.signalBand} aria-label="风险信号">
        {snapshot.signals.map((signal) => (
          <article key={signal.label} className={styles.signal + ' ' + styles[signal.level]}>
            <span>{signal.level === 'risk' ? 'RISK' : signal.level === 'watch' ? 'WATCH' : 'NORMAL'}</span>
            <strong>{signal.label}</strong>
            <p>{signal.detail}</p>
          </article>
        ))}
      </section>

      <AgentBriefs snapshot={snapshot} />

      <nav className={styles.marketRail} aria-label="市场板块快速导航">
        {order.map((id) => snapshot.groups[id] && <a key={id} href={'#' + id}>{snapshot.groups[id].title}</a>)}
      </nav>

      <div className={styles.marketGrid}>
        {order.map((id) => <GroupSection key={id} snapshot={snapshot} groupId={id} />)}
      </div>

      <section className={styles.bottomGrid}>
        <div className={styles.plainSection}>
          <div className={styles.sectionTitle}><h2>宏观压力表</h2><span>官方序列</span></div>
          <div className={styles.macroList}>
            {snapshot.macro.map((item) => (
              <div key={item.series}>
                <span>{item.label}<small>{item.market_date}</small></span>
                <strong>{formatValue(item.value)}</strong>
                <span className={item.change > 0 ? styles.negative : item.change < 0 ? styles.positive : styles.muted}>
                  {item.change > 0 ? '+' : ''}{item.change.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className={styles.plainSection}>
          <div className={styles.sectionTitle}><h2>世界事件</h2><span>原始来源优先</span></div>
          {snapshot.world_events.length ? (
            <ul className={styles.eventList}>{snapshot.world_events.map((event) => (
              <li key={event.title + '-' + event.published_at}><a href={event.url} target="_blank" rel="noreferrer">{event.title}</a><span>{event.domain}</span></li>
            ))}</ul>
          ) : <p className={styles.empty}>本次世界事件源被限流。行情数据仍有效，事件解释暂不生成。</p>}
        </div>
      </section>

      <footer className={styles.dataFooter}>
        <strong>证据边界</strong>
        <p>{snapshot.data_quality.disclaimer}</p>
        {snapshot.data_quality.failures.length > 0 && <details><summary>查看 {snapshot.data_quality.failures.length} 个数据故障</summary>
          <ul>{snapshot.data_quality.failures.map((failure) => <li key={failure.source}>{failure.source}: {failure.error}</li>)}</ul>
        </details>}
      </footer>
    </main>
  );
}
