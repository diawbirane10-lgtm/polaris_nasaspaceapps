"""Recompute the 1h versus 6h lunar geometry sampling audit.

Run with internet connectivity:
    python tools/validate_sampling.py

NASA/JPL Horizons calls are authoritative input observations. The following
visibility estimates use POLARIS 6-km local skylines, NOT a communications
link budget or a certified landing site horizon.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from api.core import Site, get_ephemeris
from api.horizon import HorizonProfile

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'data/nasa/reference_sites_2026-11-14_18.json').read_text())
CHECK=(ROOT/'data/analysis/hourly_sampling_audit_2026-11-14.json')

def rows_to_metrics(rows, skyline: HorizonProfile, start: str, end: str):
    begin=datetime.fromisoformat(start.replace('Z','+00:00'))
    finish=datetime.fromisoformat(end.replace('Z','+00:00'))
    matching=[]
    for row in rows:
        stamp=datetime.fromisoformat(row['utc'].replace('Z','+00:00'))
        if begin <= stamp < finish:
            matching.append(row)
    if not matching:
        raise ValueError('No samples in analysis window')
    step=(datetime.fromisoformat(rows[1]['utc'].replace('Z','+00:00'))-
          datetime.fromisoformat(rows[0]['utc'].replace('Z','+00:00'))).total_seconds()/3600
    hours=0;gap=0;max_gap=0
    for row in matching:
        clear = row['el_deg'] > skyline.elevation(row['az_deg'])
        if clear:
            hours += step
            gap=0
        else:
            gap+=step
            max_gap=max(max_gap,gap)
    return {'earth_clear_hours':hours,'max_gap_hours':max_gap}


def check():
    results=[]
    for key,s in DATA['sites'].items():
        profile=HorizonProfile(tuple(s['horizon_profile']['elevations_deg']),s['dem_url'])
        observer=Site(s['name'],s['lat_deg'],s['lon_e_deg'],s['observer_altitude_horizons_km'])
        hour=get_ephemeris('399',observer,'2026-11-14',4,1)
        six=get_ephemeris('399',observer,'2026-11-14',4,6)
        for start,end in [('2026-11-16T00:00Z','2026-11-17T00:00Z'),('2026-11-14T00:00Z','2026-11-18T00:00Z')]:
            a=rows_to_metrics(six,profile,start,end)
            b=rows_to_metrics(hour,profile,start,end)
            results.append({'site':key,'start_utc':start,'end_utc':end,
                           'six_hour':a,'one_hour':b,
                           'delta_clear_hours':b['earth_clear_hours']-a['earth_clear_hours']})
    return results

if __name__=='__main__':
    print(json.dumps({'method':'Hourly JPL Horizons against existing local NASA LOLA skyline',
                      'results':check(),'science_limits':json.loads(CHECK.read_text())['limitations']},indent=2))
