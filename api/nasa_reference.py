"""Real, provenance-tracked NASA reference data for the POLARIS 2026 demo.

The dataset stores *measured/interpolated terrain* and *JPL ephemeris outputs*.
Visibility and energy figures are computed by POLARIS, not supplied by NASA.
These non-flight-qualified, 6 km local skylines omit distant mountains.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .core import mission_metrics
from .horizon import HorizonProfile

DATASET = Path(__file__).resolve().parent.parent/'data'/'nasa'/'reference_sites_2026-11-14_18.json'

@lru_cache(maxsize=1)
def load_dataset() -> dict[str, Any]:
    data=json.loads(DATASET.read_text(encoding='utf-8'))
    for site in data['sites'].values():
        profile=site['horizon_profile']
        if len(profile['elevations_deg']) != 360 // profile['azimuth_step_deg']:
            raise ValueError('Horizon profile azimuth bins inconsistent')
        for name in ('sun', 'earth'):
            rows=site['ephemeris'][name]
            if len(rows)!=17 or rows[0]['utc'] != data['start_utc'] or rows[-1]['utc'] != data['end_utc']:
                raise ValueError('Incomplete reference ephemerides')
    return data


def analyze_reference(site_key: str, *, area: float=16, load: float=400,
                      battery: float=20, mode: str='horizontal') -> dict[str, Any]:
    data=load_dataset()
    site=data['sites'][site_key]
    prof=site['horizon_profile']
    skyline=HorizonProfile(tuple(prof['elevations_deg']),
                           provenance=f"NASA/GSFC LOLA 5m DEM: {site['dem_url']}; SHA256={site['dem_sha256']}; six-km ray horizon; 2m mast")
    outputs=mission_metrics(site['ephemeris']['sun'], site['ephemeris']['earth'],6,
                            pv_area_m2=area, load_w=load, battery_kwh=battery,
                            array_mode=mode, skyline=skyline)
    return {
        'site_key':site_key,
        'site':{'lat_deg':site['lat_deg'],'lon_e_deg':site['lon_e_deg'],
                'height_km':site['observer_altitude_horizons_km'],
                'name':site['name']},
        'source_type':'nasa_real_reference',
        'source':'NASA GSFC LOLA DEM (5m/pixel), JPL Horizons az/el (source results, rounded to four decimals)',
        'data_provenance':{
            'dem_url':site['dem_url'],'dem_sha256':site['dem_sha256'],
            'jpl_raw_sha256':site['jpl_raw_response_sha256'],
            'jpl_api':data['ephemeris']['source_url'],
            'longitude_frame':data['ephemeris']['frame'],
            'sample_interval_hours':6,
            'range_km':6,
            'sampling_step_azimuth_deg':5,
            'sampling_step_radial_m':50,
            'date_window_utc':[data['start_utc'],data['end_utc']],
        },
        'model':'6 km local LOLA topographic horizon, no distant-terrain or link budget model',
        'start_utc':'2026-11-14', 'duration_days':4, 'step_hours':6,
        'assumptions':{'pv_efficiency':0.28, 'pv_derate':0.78,'solar_constant_w_m2':1361,
                       'pv_area_m2':area,'panel_mode':mode,'load_w':load,
                       'battery_kwh':battery,'initial_soc_pct':80,
                       'no_distant_terrain':True,'no_radio_link_budget':True,
                       'no_precise_solar_irradiance':True},
        'limitations':[data['science_warning'],data['terrain']['horizontal_extent'],
                       data['terrain']['frame_warning'],data['site_warning']],
        **outputs
    }
