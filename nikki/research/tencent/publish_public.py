"""Export a reviewed research page using an explicit field contract.

The user requested full charts and the 3-lot scenario. Credentials, account data,
raw HTTP payloads, feature matrices and local paths remain outside this contract.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from collect import ROOT

SUMMARY_FIELDS={'schema_version','symbol','report_date','generated_at','feature_cutoff',
 'research_cutoff','prediction_id','publication_mode','report','topics','news_coverage',
 'model_evaluation','publication','schedule'}
FULL_FIELDS=SUMMARY_FIELDS|{'technical','assets','macro','quality','forecasts','analogs','chart','model_protocol','intraday'}
REPORT_FIELDS=['headline','summary','confidence','news','technical','macro','scenarios','watch','limitations']
TOPIC_FIELDS=['id','title_zh','category','event_date','published_at','published_date',
 'source_name','url','summary_zh','tencent_link','direction','relevance','verification',
 'heat_basis','market_timing','supporting_urls','claim_limit']
HKT=dt.timezone(dt.timedelta(hours=8))

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def file_hash(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)

def validate_review(folder,data,now):
    receipt=read(folder/'publication-review.json')
    date=data['report_date']
    if receipt.get('report_date')!=date or receipt.get('mode') not in ['original-research-only','full-research-page']:
        raise ValueError('Dated original-research review is required')
    reviewed=dt.datetime.fromisoformat(receipt['reviewed_at'].replace('Z','+00:00'))
    if reviewed.tzinfo is None or reviewed>now or (now-reviewed).total_seconds()>36*3600:
        raise ValueError('Publication review expired or has no valid timezone')
    required=['site-data/latest.json','synthesis.json','news-ai-compute.json',
       'news-tencent-china.json','news-global-macro.json','topic-exclusions.json']
    for name in required:
        if receipt.get('sha256',{}).get(name)!=file_hash(folder/name):
            raise ValueError(f'Review does not match {name}')
    checks=['original_summaries','market_timing_checked','no_credentials_or_local_paths'] if receipt['mode']=='full-research-page' else ['no_personal_positions','original_summaries','market_timing_checked','no_raw_market_redistribution']
    if receipt['mode']=='full-research-page' and receipt.get('user_authorized_full_page') is not True:
        raise ValueError('Explicit full-page publication authorization missing')
    for key in checks:
        if receipt.get('checks',{}).get(key) is not True:raise ValueError(f'Review check missing: {key}')
    if data.get('technical',{}).get('date')!=date:
        raise ValueError('Core market date mismatch')
    cutoff=dt.datetime.fromisoformat(data['feature_cutoff'])
    if cutoff>now:raise ValueError('Feature cutoff is still in the future')
    quality=data['quality']
    if quality.get('missing_sessions') or quality.get('unexpected_sessions'):
        raise ValueError('Unresolved market calendar gaps')
    if quality.get('resolved_conflict_count',0)!=len(quality.get('price_conflicts',[])):
        raise ValueError('Unresolved quote conflicts')
    if data['news_coverage']['window_end']!=date:raise ValueError('News window is stale')
    if data['report'].get('report_date')!=date:raise ValueError('Synthesis is stale')
    from analyze import normalize
    normalize(folder/'raw',date)
    return receipt

def export(data,now,full=False):
    topics=[]
    for t in data['topics']:
        item={k:t[k] for k in TOPIC_FIELDS if k in t}
        if urlsplit(item['url']).scheme not in ['https','http']:raise ValueError('Unsafe source URL')
        topics.append(item)
    evaluations=[]
    for window in data.get('forecasts',[]):
        for target,value in window['targets'].items():
            evaluations.append({'horizon':window['horizon'],'target':target,
              **{k:value.get(k) for k in ['status','oos_n','improvement_pct','coverage80','folds_won','fold_count']}})
    coverage={k:v for k,v in data['news_coverage'].items() if k!='duplicates_removed'}
    payload={k:data[k] for k in ['schema_version','symbol','report_date','generated_at',
      'feature_cutoff','research_cutoff','prediction_id']}
    payload.update(publication_mode='public-original-research',
      report={k:data['report'][k] for k in REPORT_FIELDS},topics=topics,news_coverage=coverage,
      model_evaluation=evaluations,
      publication={'published_at':now.isoformat(),'raw_market_data_included':False,
        'note':'公开原创研究与来源链接；完整K线、行情数据库和个人信息保留在本地。'},
      schedule={'timezone':'Asia/Shanghai','start_time':'19:10','mode':'Codex local heartbeat + GitHub Actions Pages',
        'note':'每日19:10启动；港股交易日发布新报告，休市保留上一交易日。完成研究、校验及部署后更新。'})
    if full:
        payload.update({k:data[k] for k in ['technical','assets','macro','quality','forecasts','analogs','chart','model_protocol','intraday']})
        payload['publication_mode']='public-full-research'
        payload['publication']={'published_at':now.isoformat(),'raw_market_data_included':True,
          'user_authorized_full_page':True,'note':'用户要求恢复完整研究页面：K线、指标、全球资产、模型、话题及3手操作情景。数值为研究快照，不是实时行情。'}
        payload['schedule']['note']='每日19:10启动并更新完整研究、30/120分钟与未来3交易日情景；不是盘中实时监控。休市保留最近交易日。'
    validate_public(payload)
    return payload

def validate_public(payload):
    full=payload.get('publication_mode')=='public-full-research'
    if set(payload)!=(FULL_FIELDS if full else SUMMARY_FIELDS):raise ValueError('Unexpected public fields')
    encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False)
    for pattern in [r'(?i)(api[_-]?key|authorization|access[_-]?token)\s*[=:]',
                    r'[A-Z]:[\\/]',r'(?i)file://',r'(?i)research-private',
                    r'(?i)\b(access_token|client_secret|password)\b']:
        if re.search(pattern,encoded):raise ValueError('Private field or local path found')
    if len({t['id'] for t in payload['topics']})!=len(payload['topics']):raise ValueError('Duplicate topic IDs')
    if len(payload['topics'])<100 or payload['news_coverage'].get('technology_topics',0)<100:
        raise ValueError('At least 100 technology topics are required')
    if full:
        if payload['publication'].get('user_authorized_full_page') is not True:raise ValueError('Full-page authorization missing')
        if not payload['chart']['daily'] or not payload['intraday']['chart']['m30']:raise ValueError('Full page requires actual chart data')
    elif payload['publication']['raw_market_data_included'] is not False:raise ValueError('Unexpected market export')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-close-v[12]-[a-f0-9]{12}',payload['prediction_id']):
        raise ValueError('Invalid prediction identifier')

def main():
    p=argparse.ArgumentParser();p.add_argument('--date');p.add_argument('--verify-public',type=Path);a=p.parse_args()
    if a.verify_public:
        validate_public(read(a.verify_public));print('Public field and privacy checks passed');return
    if not a.date:p.error('--date required')
    folder=ROOT/'research-private'/f'tencent-{a.date}'
    data=read(folder/'site-data/latest.json');now=dt.datetime.now(dt.timezone.utc)
    if data['report_date']!=a.date:raise ValueError('Requested report date mismatch')
    receipt=validate_review(folder,data,now);payload=export(data,now,full=receipt['mode']=='full-research-page')
    dest=ROOT/'nikki/site/public/data/tencent'
    latest=dest/'latest.json'
    if latest.exists() and read(latest)['report_date']>a.date:raise ValueError('Cannot overwrite newer report')
    archive=dest/'archive'/f'{data["prediction_id"]}.json'
    if not archive.exists():atomic_json(archive,payload)
    atomic_json(latest,payload)
    print(json.dumps({'report_date':a.date,'prediction_id':data['prediction_id'],'topics':len(payload['topics']),'mode':payload['publication_mode']},ensure_ascii=False))

if __name__=='__main__':main()
