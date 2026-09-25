import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from daily_sources import select_daily,quote_turnover
from analyze import resample
from collect import repair_yahoo_nulls

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')

class SourceFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.raw=self.root/'tencent-2026-09-25/raw'
        self.days=[['2026-09-23','440','441','443','438','100'],
                   ['2026-09-24','434','435','437','432','100'],
                   ['2026-09-25','433','436','438','431','100']]
        quote=['0']*78
        for i,v in {2:'00700',3:'436',6:'100',30:'2026/09/25 16:08:20',37:'43450',59:'0.1',75:'HKD'}.items():quote[i]=v
        self.tx={'_source_url':'https://example.test/quote','_fetched_at':'2026-09-25T11:00:00Z',
                 'data':{'hk00700':{'day':self.days,'qt':{'hk00700':quote}}}}
        write(self.raw/'collection.json',{'date':'2026-09-25','errors':[{'source':'eastmoney'}]})
        write(self.raw/'tencent-crosscheck.json',self.tx)
        self.cache=self.root/'tencent-2026-09-23/raw/eastmoney.json'
        write(self.cache,{'fetched_at':'2026-09-23T11:00:00Z','payload':{'data':{'code':'00700','klines':[
            '2026-09-23,440,441,443,438,100,44100,0,0,0,0.1']}}})
    def test_fallback_preserves_date_and_missing_amount(self):
        frame,meta=select_daily(self.raw,'2026-09-25',self.root)
        self.assertEqual(meta['provider'],'tencent')
        self.assertEqual(frame.loc['2026-09-23','turnover'],44100)
        self.assertTrue(pd.isna(frame.loc['2026-09-24','turnover']))
        self.assertEqual(frame.loc['2026-09-25','turnover'],43450)
        self.assertNotEqual(frame.loc['2026-09-25','turnover'],436*100)
        self.assertEqual(meta['missing_turnover_dates'],['2026-09-24'])
    def test_stale_quote_cannot_fill_today_amount(self):
        self.tx['data']['hk00700']['qt']['hk00700'][30]='2026/09/24 16:08:20'
        write(self.raw/'tencent-crosscheck.json',self.tx)
        frame,_=select_daily(self.raw,'2026-09-25',self.root)
        self.assertTrue(pd.isna(frame.loc['2026-09-25','turnover']))
    def test_cached_different_prices_are_not_reused(self):
        cached=json.loads(self.cache.read_text());cached['payload']['data']['klines'][0]='2026-09-23,440,442,443,438,100,44100,0,0,0,0.1';write(self.cache,cached)
        frame,_=select_daily(self.raw,'2026-09-25',self.root)
        self.assertTrue(pd.isna(frame.loc['2026-09-23','turnover']))
    def test_stale_primary_rejected(self):
        self.tx['data']['hk00700']['day']=self.days[:-1];write(self.raw/'tencent-crosscheck.json',self.tx)
        with self.assertRaisesRegex(ValueError,'latest day is stale'):select_daily(self.raw,'2026-09-25',self.root)
    def test_missing_both_providers_rejected(self):
        write(self.raw/'collection.json',{'date':'2026-09-25','errors':[{'source':'eastmoney'},{'source':'tencent-crosscheck'}]})
        with self.assertRaisesRegex(ValueError,'No current primary'):select_daily(self.raw,'2026-09-25',self.root)
    def test_failed_attempt_does_not_reuse_old_file(self):
        write(self.raw/'eastmoney.json',json.loads(self.cache.read_text()))
        frame,meta=select_daily(self.raw,'2026-09-25',self.root)
        self.assertEqual(meta['provider'],'tencent')
    def test_period_turnover_remains_missing(self):
        frame,_=select_daily(self.raw,'2026-09-25',self.root)
        frame=frame.rename(columns={'high':'high_observed','low':'low_observed'})
        weekly=resample(frame,'W-FRI')
        self.assertTrue(pd.isna(weekly[-1]['turnover']))
    def test_amount_scale_and_currency_guard(self):
        q=self.tx['data']['hk00700']['qt']['hk00700'];q[37]='43450000'
        self.assertIsNone(quote_turnover(self.tx,'2026-09-25',{'close':436,'volume':100,'low':431,'high':438}))
    def test_yahoo_null_repair_only_same_timestamp(self):
        stamp=int(dt.datetime(2026,9,25,1,30,tzinfo=dt.timezone.utc).timestamp())
        def payload(stamps,closes):return {'fetched_at':'2026-09-25T11:00:00Z','payload':{'chart':{'result':[{'meta':{'symbol':'0700.HK','exchangeTimezoneName':'Asia/Hong_Kong'},'timestamp':stamps,'indicators':{'quote':[{'close':closes}]}}]}}}
        write(self.raw/'0700.HK.json',payload([stamp],[436.6]))
        new=payload([stamp,stamp+86400],[None,None])
        fixed=repair_yahoo_nulls(new,'0700.HK','2026-09-25',self.root)
        self.assertEqual(fixed['payload']['chart']['result'][0]['indicators']['quote'][0]['close'],[436.6,None])
        self.assertEqual(len(fixed['same_timestamp_repairs']),1)
    def test_yahoo_intraday_snapshot_not_promoted_to_daily_close(self):
        stamp=int(dt.datetime(2026,9,25,1,30,tzinfo=dt.timezone.utc).timestamp())
        old={'fetched_at':'2026-09-25T04:00:00Z','payload':{'chart':{'result':[{'meta':{'symbol':'0700.HK','exchangeTimezoneName':'Asia/Hong_Kong'},'timestamp':[stamp],'indicators':{'quote':[{'close':[450.]}]}}]}}}
        write(self.raw/'0700.HK.json',old);new=copy.deepcopy(old);new['payload']['chart']['result'][0]['indicators']['quote'][0]['close']=[None]
        fixed=repair_yahoo_nulls(new,'0700.HK','2026-09-25',self.root)
        self.assertIsNone(fixed['payload']['chart']['result'][0]['indicators']['quote'][0]['close'][0])

if __name__=='__main__':unittest.main()
