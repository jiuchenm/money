export type SparkPoint = {date: string; value: number};

export type MarketAsset = {
  symbol: string;
  name: string;
  market_date: string;
  value: number;
  change_1d: number;
  change_5d: number | null;
  change_20d: number | null;
  drawdown_1y: number;
  sma_50: number | null;
  sma_200: number | null;
  above_50d: boolean | null;
  above_200d: boolean | null;
  volatility_20d: number | null;
  sparkline: SparkPoint[];
  source: string;
};

export type MarketGroup = {
  id: string;
  title: string;
  status: 'ok' | 'partial';
  assets: Record<string, MarketAsset>;
};

export type AgentNote = {
  headline: string;
  stance: string | Record<string, string>;
  forces: string[];
  divergences: string[];
  triggers: string[];
  invalidations: string[];
  confidence: string | {level: string; reason: string};
};

export type WorldEvent = {
  title: string;
  url?: string;
  domain?: string;
  published_at?: string;
  language?: string;
  source: string;
  source_tier?: 'primary' | 'recognized_media';
  evidence_status?: string;
  chinese_summary?: string;
  hk_a_impact?: string;
  affected_assets?: string[];
  mechanism?: string;
  priced_in?: string;
  event_kind?: 'fact' | 'metric_methodology' | 'market_reaction';
  metric_caveat?: string;
  coverage_topic?: string;
};

export type NikkiSnapshot = {
  schema_version: number;
  report_date: string;
  fetched_at: string;
  timezone: string;
  market_phase_note: string;
  groups: Record<string, MarketGroup>;
  macro: Array<{series: string; label: string; market_date: string; value: number; change: number; source: string}>;
  world_events: WorldEvent[];
  world_events_status?: 'collected' | 'insufficient_evidence';
  world_events_coverage?: Record<string, string>;
  signals: Array<{level: 'calm' | 'watch' | 'risk'; label: string; detail: string}>;
  agent_notes: Record<string, AgentNote>;
  data_quality: {status: string; failures: Array<{source: string; error: string}>; disclaimer: string};
};
