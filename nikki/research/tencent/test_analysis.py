import unittest
import numpy as np
import pandas as pd
from analyze import make_labels,resample,normalize,wealth_index
from collect import ROOT

class PathTests(unittest.TestCase):
    def frame(self,closes):
        f=pd.DataFrame({'close':closes},index=pd.date_range('2026-01-01',periods=len(closes),freq='B'))
        for c in ['open','high_observed','low_observed']:f[c]=f.close
        f['conflict']=False;f['dividend']=False;f['volume']=10;f['turnover']=1000
        return f
    def test_up_then_drawdown_is_not_adverse_excursion(self):
        f=self.frame([100,110,103,104,104,104])
        t=make_labels(f)[5].iloc[0]
        self.assertAlmostEqual(t.upside,.10)
        self.assertAlmostEqual(t.downside,0)
        self.assertAlmostEqual(t.drawdown,1-103/110)
    def test_same_day_barrier_order_is_unknown(self):
        f=self.frame([100]*6);f.iloc[1,f.columns.get_loc('high_observed')]=106;f.iloc[1,f.columns.get_loc('low_observed')]=94
        self.assertEqual(make_labels(f)[5].iloc[0].first_hit,2)
    def test_unmatured_and_dividend_labels_are_missing(self):
        f=self.frame([100]*6)
        self.assertTrue(make_labels(f)[5].iloc[-1].isna().all())
        f.iloc[3,f.columns.get_loc('dividend')]=True
        self.assertTrue(make_labels(f)[5].iloc[0].isna().all())
    def test_resample_sums_turnover_and_marks_partial(self):
        f=self.frame([100,101,102]);b=resample(f,'ME')[-1]
        self.assertEqual(b['volume'],30);self.assertEqual(b['turnover'],3000);self.assertTrue(b['partial'])
    def test_stale_daily_snapshot_is_not_relabelled(self):
        raw=ROOT/'research-private/tencent-2026-09-22/raw'
        if not raw.exists():self.skipTest('private fixture absent')
        with self.assertRaisesRegex(ValueError,'Stale core data'):
            normalize(raw,'2026-09-23')
    def test_opening_gap_identifies_first_barrier(self):
        f=self.frame([100]*6)
        f.iloc[1,f.columns.get_loc('open')]=106;f.iloc[1,f.columns.get_loc('high_observed')]=107;f.iloc[1,f.columns.get_loc('low_observed')]=94
        self.assertEqual(make_labels(f)[5].iloc[0].first_hit,1)
    def test_cash_dividend_does_not_become_negative_momentum(self):
        idx=pd.date_range('2026-01-01',periods=3)
        wealth=wealth_index(pd.Series([100.,95.,96.],index=idx),pd.Series([0.,5.,0.],index=idx))
        self.assertAlmostEqual(wealth.iloc[1],100.)
        self.assertAlmostEqual(wealth.iloc[2],100*96/95)

if __name__=='__main__':unittest.main()
