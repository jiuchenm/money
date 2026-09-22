"""Build a private, auditable research snapshot; publishing is separate."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
from urllib.parse import urlsplit,urlunsplit
from collect import ROOT

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def canonical_url(url):
    u=urlsplit(url);return urlunsplit((u.scheme,u.netloc.lower().removeprefix('www.'),u.path.rstrip('/'),'',''))

def main():
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);a=p.parse_args()
    folder=ROOT/'research-private'/f'tencent-{a.date}';data=load(folder/'analysis.json')
    window_start=(dt.date.fromisoformat(a.date)-dt.timedelta(days=30)).isoformat()
    if data.get('report_date')!=a.date or data.get('technical',{}).get('date')!=a.date:
        raise SystemExit('Analysis date does not match requested trading date')
    topics=[];duplicates=[];seen=set()
    for name in ['news-ai-compute.json','news-tencent-china.json','news-global-macro.json']:
        raw=load(folder/name);rows=raw if isinstance(raw,list) else raw['topics']
        for item in rows:
            for key in ['id','title_zh','category','url','summary_zh','source_name','tencent_link','relevance','verification','heat_basis']:
                if not item.get(key): raise ValueError(f'Missing {key} in {name}')
            item.setdefault('published_at',None);item.setdefault('available_at',None)
            dated=(item.get('published_at') or item.get('published_date') or item.get('event_date') or '')[:10]
            if dated and not window_start<=dated<=a.date:
                duplicates.append({'id':item['id'],'url':item['url'],'reason':'outside rolling 30-day window'});continue
            # Retrieved-at fallback proves only when we observed the page, not
            # that an old event was first public after today's close.
            timestamp=item.get('published_at')
            item['market_timing']='time_unknown'
            if timestamp and 'T' in timestamp:
                when=dt.datetime.fromisoformat(timestamp.replace('Z','+00:00'))
                if when.tzinfo is not None:
                    close=dt.datetime.fromisoformat(a.date+'T16:10:00+08:00')
                    item['market_timing']='before_close' if when<=close else 'after_close'
            key=canonical_url(item['url'])
            if key in seen:duplicates.append({'id':item['id'],'url':item['url'],'reason':'same canonical source'});continue
            seen.add(key);topics.append(item)
    exclusions_path=folder/'topic-exclusions.json'
    exclusions=load(exclusions_path) if exclusions_path.exists() else {}
    for item in topics[:]:
        if item['id'] in exclusions:
            duplicates.append({'id':item['id'],'url':item['url'],'reason':exclusions[item['id']]});topics.remove(item)
    topics.sort(key=lambda v:({'direct':0,'indirect':1,'background':2}.get(v['relevance'],3),-(int(re.sub('[^0-9]','',str(v.get('published_at') or v.get('published_date') or v.get('event_date') or ''))[:8] or '0'))))
    if len(topics)<100:raise SystemExit(f'Only {len(topics)} unique topics; cannot claim 100')
    data['topics']=topics
    data['news_coverage']={'unique_topics':len(topics),'window_start':window_start,'window_end':a.date,
        'verified':sum(t['verification']=='verified' for t in topics),'partial':sum(t['verification']!='verified' for t in topics),
        'duplicates_removed':duplicates,'technology_topics':sum(t['category'] not in ['macro_rates','hong_kong_liquidity'] for t in topics),
        'after_close_topics':sum(t['market_timing']=='after_close' for t in topics),
        'note':'近期公司发布与媒体报道构成候选话题池，先近7日、再扩至30日；不是全网热搜排名。主题数量不作为利好投票，日期与来源保留，媒体转述和公司自述分别标记。'}
    data['report']=load(folder/'synthesis.json')
    if data['report'].get('report_date')!=a.date:
        raise SystemExit('Synthesis must carry this trading report_date')
    supplement=folder/'macro-supplement.json'
    if supplement.exists():data['macro']+=load(supplement)['items']
    data['publication_mode']='private-local-research'
    data['research_cutoff']=dt.datetime.now(dt.timezone.utc).isoformat()
    stable={k:v for k,v in data.items() if k not in ['research_cutoff','prediction_id']}
    data['prediction_id']=a.date+'-close-v1-'+hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest()[:12]
    out=folder/'site-data/latest.json';save(out,data)
    archive=folder/'site-data/archive'/f'{data["prediction_id"]}.json'
    if not archive.exists():save(archive,data)
    save(folder/'assembly-quality.json',{'unique_topics':len(topics),'duplicates':duplicates,'prediction_id':data['prediction_id'],'output':str(out)})
    print(json.dumps({'topics':len(topics),'verified':data['news_coverage']['verified'],'partial':data['news_coverage']['partial'],'output':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
