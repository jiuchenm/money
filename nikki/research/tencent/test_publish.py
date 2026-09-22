import copy
import datetime as dt
import unittest
from collect import ROOT
from publish_public import export,read,validate_public

class PublicationTests(unittest.TestCase):
    def setUp(self):
        p=ROOT/'research-private/tencent-2026-09-22/site-data/latest.json'
        if not p.exists():self.skipTest('private fixture absent')
        self.public=export(read(p),dt.datetime.now(dt.timezone.utc))
    def test_raw_market_data_is_not_exported(self):
        for name in ['chart','technical','assets','macro','quality','forecasts','analogs']:
            self.assertNotIn(name,self.public)
        self.assertFalse(self.public['publication']['raw_market_data_included'])
    def test_unexpected_private_fields_are_rejected(self):
        d=copy.deepcopy(self.public);d['portfolio']={'quantity':100}
        with self.assertRaisesRegex(ValueError,'Unexpected public fields'):validate_public(d)
    def test_nested_local_paths_are_rejected(self):
        d=copy.deepcopy(self.public);d['report']['summary']='See C:/Users/private.json'
        with self.assertRaisesRegex(ValueError,'Private field'):validate_public(d)
    def test_macro_topics_do_not_satisfy_technology_minimum(self):
        d=copy.deepcopy(self.public);d['news_coverage']['technology_topics']=99
        with self.assertRaisesRegex(ValueError,'100 technology'):validate_public(d)

if __name__=='__main__':unittest.main()
