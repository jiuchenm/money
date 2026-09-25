"""Stock Connect execution availability differs from the HK price calendar."""
import datetime as dt
import pandas as pd
import exchange_calendars as xcals

SOURCE='https://www.sse.com.cn/services/hkexsc/disclo/announ/c/c_20251222_10802519.shtml'
PERIODS=[('2026-01-01','2026-01-03'),('2026-02-15','2026-02-23'),
 ('2026-04-03','2026-04-07'),('2026-05-01','2026-05-05'),('2026-05-25','2026-05-25'),
 ('2026-06-19','2026-06-21'),('2026-07-01','2026-07-01'),('2026-09-25','2026-09-27'),
 ('2026-10-01','2026-10-07'),('2026-10-19','2026-10-19'),('2026-12-25','2026-12-25')]

def connect_open(day,time=None):
    day=pd.Timestamp(day).date()
    if day.year!=2026:raise ValueError('Stock Connect calendar year requires official refresh')
    if not xcals.get_calendar('XHKG').is_session(pd.Timestamp(day)):return False
    if any(dt.date.fromisoformat(a)<=day<=dt.date.fromisoformat(b) for a,b in PERIODS):return False
    if str(day) in ['2026-12-24','2026-12-31'] and time is not None and time>=dt.time(12):return False
    return True

def next_connect_sessions(asof,count=3):
    candidates=xcals.get_calendar('XHKG').sessions_in_range(pd.Timestamp(asof)+pd.Timedelta(days=1),pd.Timestamp(asof)+pd.Timedelta(days=35))
    days=[d for d in candidates if connect_open(d)]
    if len(days)<count:raise ValueError('Insufficient verified Stock Connect sessions')
    return days[:count]
