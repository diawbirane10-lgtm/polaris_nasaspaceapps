"""Reproducible counterfactual experiments on stored NASA observations.

The local LOLA 6-km horizon can establish a *local obstruction*, but cannot
establish that more distant terrain is clear. No flight/safety recommendations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import math
from typing import Any

from .core import mission_metrics
from .horizon import HorizonProfile
from .nasa_reference import DATASET, load_dataset


def _date(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError('UTC timestamp required, e.g. 2026-11-14T00:00Z')
    if dt.minute or dt.second or dt.microsecond or dt.hour % 6:
        raise ValueError('Timestamp must align to a 6-hour NASA sample')
    return dt


def _rows(site: dict, body: str, begin: datetime, end: datetime) -> list[dict]:
    out = [r for r in site['ephemeris'][body] if begin <= _date(r['utc']) <= end]
    expected = int((end - begin).total_seconds() / 21600) + 1
    if len(out) != expected or not out or _date(out[0]['utc']) != begin or _date(out[-1]['utc']) != end:
        raise ValueError('Requested window is outside the stored NASA ephemerides')
    for prev, nxt in zip(out, out[1:]):
        if _date(nxt['utc']) - _date(prev['utc']) != timedelta(hours=6):
            raise ValueError('A 6-hour observation is missing')
    return out


def _evaluate(site_key: str, begin: datetime, hours: int, *, pv_area_m2: float,
              load_w: float, battery_kwh: float, mode: str) -> dict[str, Any]:
    source = load_dataset()['sites'][site_key]
    end = begin + timedelta(hours=hours)
    profile = HorizonProfile(tuple(source['horizon_profile']['elevations_deg']),
                             provenance=source['dem_url'])
    result = mission_metrics(_rows(source, 'sun', begin, end),
                             _rows(source, 'earth', begin, end), 6,
                             pv_area_m2=pv_area_m2, load_w=load_w,
                             battery_kwh=battery_kwh, array_mode=mode,
                             skyline=profile)
    s = result['summary']
    return {
        'site_key': site_key,
        'site_name': source['name'],
        'start_utc': begin.strftime('%Y-%m-%dT%H:%MZ'),
        'end_utc': end.strftime('%Y-%m-%dT%H:%MZ'),
        'summary': s,
        'local_earth_blocked_hours': round(hours - s['earth_visible_hours'], 2),
        'earth_clear_upper_bound_hours': s['earth_visible_hours'],
        'local_solar_illumination_upper_bound_hours': s['sun_visible_hours'],
        'energy_note': 'Optimistic energy bound: unmodeled distant terrain may reduce collection',
    }


def counterfactual(*, site_key: str='connecting_ridge', start_utc: str='2026-11-14T00:00Z',
                   duration_hours: int=24, delay_hours: int=48, pv_area_m2: float=16,
                   load_w: float=400, battery_kwh: float=20,
                   mode: str='horizontal') -> dict[str, Any]:
    """Compare original, delayed and alternate-location schedules on same NASA data.

    No scalar total 'best site' score is constructed. Deltas have transparent
    direction and depend on the declared load and panel assumptions.
    """
    data = load_dataset()
    if site_key not in data['sites']:
        raise ValueError('Unknown NASA reference site')
    if duration_hours not in (24,48) or delay_hours not in (6,12,18,24,30,36,42,48,54,60,66,72):
        raise ValueError('Duration must be 24/48h and delay must be a 6h multiple in 6..72h')
    if not all(math.isfinite(v) for v in (pv_area_m2, load_w, battery_kwh)):
        raise ValueError('Nonfinite power system inputs')
    if not (0 < pv_area_m2 <= 200 and 0 <= load_w <= 100000 and 0 < battery_kwh <= 10000):
        raise ValueError('Invalid power system inputs')
    if mode not in ('horizontal','tracking'):
        raise ValueError('Invalid PV orientation')
    begin = _date(start_utc)
    limit_start = _date(data['start_utc'])
    limit_end = _date(data['end_utc'])
    shifted = begin + timedelta(hours=delay_hours)
    if begin < limit_start or shifted + timedelta(hours=duration_hours) > limit_end:
        raise ValueError('Mission plus delay exceeds stored four-day reference window')
    options = {'pv_area_m2':pv_area_m2,'load_w':load_w,'battery_kwh':battery_kwh,'mode':mode}
    alternative = next(k for k in data['sites'] if k != site_key)
    baseline = _evaluate(site_key,begin,duration_hours,**options)
    delayed = _evaluate(site_key,shifted,duration_hours,**options)
    alternate = _evaluate(alternative,shifted,duration_hours,**options)

    stress = []
    for label, load_multiplier, pv_multiplier in (
        ('nominal',1.0,1.0),('load_plus_20pct',1.2,1.0),
        ('pv_area_minus_20pct',1.0,0.8),('combined_stress',1.2,0.8),
    ):
        test = _evaluate(site_key,shifted,duration_hours,**{
            **options,'load_w':load_w*load_multiplier,'pv_area_m2':pv_area_m2*pv_multiplier
        })
        stress.append({'id':label,'load_w':round(load_w*load_multiplier,3),
                       'area_m2':round(pv_area_m2*pv_multiplier,3),
                       'min_soc_pct':test['summary']['min_soc_pct'],
                       'unserved_energy_kwh':test['summary']['unserved_energy_kwh']})

    keys = ('sun_visible_hours','earth_visible_hours','max_dark_hours',
            'max_earth_gap_hours','min_soc_pct','unserved_energy_kwh')
    def delta(a,b):
        return {k:round(b['summary'][k]-a['summary'][k],3) for k in keys}

    sha = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    return {
        'analysis_type':'counterfactual_v0.4',
        'dataset_sha256':sha,
        'data_kind':'JPL Horizons az/el + local NASA/GSFC LOLA 5m DEM-derived skyline',
        'site_key':site_key,'comparison_site_key':alternative,
        'inputs':{'start_utc':start_utc,'duration_hours':duration_hours,
                  'delay_hours':delay_hours,**options},
        'scenarios':{'original':baseline,'delayed':delayed,'alternative_site_after_delay':alternate},
        'changes':{'delay_same_site':delta(baseline,delayed),
                   'site_change_at_delayed_time':delta(delayed,alternate)},
        'delayed_site_energy_sensitivity':stress,
        'recommendation':None,
        'interpretation':'Comparison only; no certified site ranking or robust mission-feasibility claim',
        'confidence':'Limited local geometric evidence (2m mast, 6km terrain, 5-degree bins, 6h samples)',
        'scientific_limits':[
            'Earth above local horizon is a potential line-of-sight upper bound, not confirmed direct-to-Earth communication.',
            'A local obstruction can establish blocked geometry; terrain beyond 6km is not included.',
            'Solar exposure and computed photovoltaic energy may be overestimated due to unknown distant shadows.',
            'Energy and battery model is illustrative, ignores losses, dust, thermal loads and subsystems.',
            'Scenarios are compared on sampled left-endpoint values at six-hour cadence.',
            'Both points are NASA dataset sampling sites, not certified safe lunar landing sites.'
        ]
    }
