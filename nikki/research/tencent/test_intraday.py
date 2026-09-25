import unittest
import pandas as pd
from intraday import aggregate120,simulate,fee_estimate
from trading_calendar import connect_open,next_connect_sessions

class IntradayTests(unittest.TestCase):
    def frame(self,days=3):
        rows=[]
        for date in pd.bdate_range('2026-09-14',periods=days):
            for hhmm in ['09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00','15:30']:
                t=pd.Timestamp(str(date.date())+' '+hhmm,tz='Asia/Hong_Kong')
                rows.append({'time':t,'open':450.,'high':451.,'low':449.,'close':450.,'volume':100.,'turnover':45000.,'sell_trigger':False})
        return pd.DataFrame(rows).set_index('time')
    def daily(self):
        return pd.DataFrame({'close':[450.]*8,'atr14':[10.]*8},index=pd.bdate_range('2026-09-09',periods=8))
    def test_120_never_bridges_lunch_or_residual(self):
        bars,res=aggregate120(self.frame(1))
        self.assertEqual(len(bars),2);self.assertEqual(len(res),2)
        self.assertEqual(list(bars.bar_end.dt.strftime('%H:%M')),['11:30','15:00'])
        self.assertEqual(list(bars.volume),[400.,400.])
    def test_late_signal_cannot_fill_outside_three_day_window(self):
        frame=self.frame();frame.iloc[-1,frame.columns.get_loc('sell_trigger')]=True
        r=simulate(frame,self.daily(),frame.index[0].date(),3,False,True)
        self.assertEqual(r['sold_lots'],0);self.assertAlmostEqual(r['delta_hkd'],0)
    def test_sale_friction_counts_against_holding(self):
        frame=self.frame();r=simulate(frame,self.daily(),frame.index[0].date(),1,False,False)
        self.assertEqual(r['ending_lots'],2);self.assertAlmostEqual(r['delta_hkd'],-90.)
    def test_round_trip_counts_both_sides_and_caps_inventory(self):
        frame=self.frame();frame.iloc[1,frame.columns.get_loc('low')]=444.
        r=simulate(frame,self.daily(),frame.index[0].date(),1,True,False)
        self.assertEqual(r['ending_lots'],3);self.assertEqual(r['rebought_lots'],1)
        self.assertAlmostEqual(r['delta_hkd'],321.)
    def test_stamp_duty_rounding(self):
        f=fee_estimate(451.6,100,0,0,0)
        self.assertAlmostEqual(f['official_hkd'],51.74,places=2)
    def test_connect_closure_is_not_hk_price_session(self):
        self.assertFalse(connect_open('2026-09-25'))
        self.assertEqual([str(v.date()) for v in next_connect_sessions('2026-09-23')],['2026-09-24','2026-09-28','2026-09-29'])

if __name__=='__main__':unittest.main()
