import {useEffect, useState} from 'react';
import NikkiDashboard from './features/nikki/NikkiDashboard';
import type {NikkiSnapshot} from './features/nikki/types';
import latest from './data/latest.json';
import archive from './data/archive.json';
import history from './data/history.json';
import styles from './features/nikki/nikki.module.css';

type Route = {view: 'latest' | 'trends' | 'archive' | 'day'; date?: string};

function routeFromHash(): Route {
  const path = window.location.hash.replace(/^#/, '') || '/';
  if (path === '/trends') return {view: 'trends'};
  if (path === '/archive') return {view: 'archive'};
  if (path.startsWith('/archive/')) return {view: 'day', date: path.slice('/archive/'.length)};
  return {view: 'latest'};
}

function Shell({title, subtitle, children}: {title: string; subtitle: string; children: React.ReactNode}) {
  return <main className={styles.page}><header className={styles.header}><div>
    <p className={styles.eyebrow}>NIKKI · 港A市场雷达</p><h1>{title}</h1><p className={styles.subhead}>{subtitle}</p>
  </div><nav className={styles.tabs} aria-label="Nikki 页面"><a href="#/">最新</a><a href="#/trends">趋势</a><a href="#/archive">归档</a></nav></header>{children}</main>;
}

function Trends() {
  const series = Object.values(history.series);
  return <Shell title="港A历史趋势" subtitle={'已保存 ' + history.generated_from + ' 个每日快照，只跟踪恒指、恒生科技、沪深300与创业板。'}>
    {history.generated_from < 2 && <div className={styles.trendEmpty}>目前只有一个每日样本。连续运行后，下方将连接跨日变化。</div>}
    <div className={styles.trendGrid}>{series.map((item) => <section key={item.symbol} className={styles.trendPanel}>
      <div className={styles.sectionTitle}><h2>{item.name}</h2><span>每日收盘</span></div>
      <div className={styles.trendValues}>{item.points.map((point) => <div key={point.report_date}><span>{point.report_date}</span><strong>{point.value.toLocaleString('zh-CN')}</strong><em className={point.change_1d >= 0 ? styles.positive : styles.negative}>{point.change_1d > 0 ? '+' : ''}{point.change_1d.toFixed(2)}%</em></div>)}</div>
    </section>)}</div>
  </Shell>;
}

function Archive() {
  return <Shell title="每日市场档案" subtitle="每份报告保留当时价格、来源状态和 Agent 判断。">
    <ul className={styles.archiveList}>{archive.map((item) => <li key={item.date}><a href={'#/archive/' + item.date}>{item.date}</a><span>{new Date(item.fetched_at).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false})}</span><span>{item.status}</span></li>)}</ul>
  </Shell>;
}

function Day({date}: {date: string}) {
  const [snapshot, setSnapshot] = useState<NikkiSnapshot | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'data/daily/' + date + '.json').then((response) => {
      if (!response.ok) throw new Error('not found');
      return response.json();
    }).then(setSnapshot).catch(() => setError(true));
  }, [date]);
  if (error) return <Shell title="档案不存在" subtitle={date}><div className={styles.trendEmpty}>没有找到这个日期的报告。</div></Shell>;
  if (!snapshot) return <Shell title="读取档案" subtitle={date}><div className={styles.trendEmpty}>正在加载...</div></Shell>;
  return <NikkiDashboard snapshot={snapshot} archived />;
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  useEffect(() => { const update = () => setRoute(routeFromHash()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);
  if (route.view === 'trends') return <Trends />;
  if (route.view === 'archive') return <Archive />;
  if (route.view === 'day' && route.date) return <Day date={route.date} />;
  return <NikkiDashboard snapshot={latest as NikkiSnapshot} />;
}
