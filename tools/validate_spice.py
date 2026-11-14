"""Recheck bundled NASA/JPL Horizons samples independently with NAIF SPICE.

Usage:
  pip install spiceypy numpy
  python tools/validate_spice.py --download
  python tools/validate_spice.py  # reuse downloaded, SHA-checked kernels

Caution: downloads ~46MB of official NAIF kernels on first run. Does not modify
mission results or assert terrain/radio validity. All results on UTC timestamps.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import urllib.request

BASE=Path(__file__).resolve().parents[1]
REPORT=BASE/'data'/'analysis'/'spice_crosscheck_2026-11-14.json'
DATA=BASE/'data'/'nasa'/'reference_sites_2026-11-14_18.json'
URL='https://naif.jpl.nasa.gov/pub/naif/generic_kernels/'
PATHS={
 'naif0012.tls':'lsk/naif0012.tls',
 'de440s.bsp':'spk/planets/de440s.bsp',
 'pck00011.tpc':'pck/pck00011.tpc',
 'moon_pa_de440_200625.bpc':'pck/moon_pa_de440_200625.bpc',
 'moon_de440_250416.tf':'fk/satellites/moon_de440_250416.tf'
}

def download_kernels(folder:Path, enable:bool)->list[Path]:
    checks=json.loads(REPORT.read_text())['kernels_sha256']
    folder.mkdir(parents=True,exist_ok=True)
    paths=[]
    for name,sub in PATHS.items():
        target=folder/name
        if not target.exists():
            if not enable:raise FileNotFoundError(f'Missing {name}; rerun with --download')
            with urllib.request.urlopen(URL+sub,timeout=120) as response, target.open('wb') as out:
                while part:=response.read(1<<18):out.write(part)
        h=hashlib.sha256(target.read_bytes()).hexdigest()
        if h!=checks[name]:raise ValueError(f'Kernel SHA mismatch {name}: {h}')
        paths.append(target)
    return paths

def validate(kernels:list[Path])->dict:
    import spiceypy as sp
    import numpy as np
    sp.kclear()
    try:
        for p in kernels:sp.furnsh(str(p))
        source=json.loads(DATA.read_text())
        scores=[]
        for key,site in source['sites'].items():
            lat=math.radians(site['lat_deg']);lon=math.radians(site['lon_e_deg'])
            r=1737.4+site['observer_altitude_horizons_km']
            obs=[r*math.cos(lat)*math.cos(lon),r*math.cos(lat)*math.sin(lon),r*math.sin(lat)]
            up=np.array([math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)])
            east=np.array([-math.sin(lon),math.cos(lon),0.0])
            north=np.array([-math.sin(lat)*math.cos(lon),-math.sin(lat)*math.sin(lon),math.cos(lat)])
            for body in ('sun','earth'):
                diffs=[]
                for row in site['ephemeris'][body]:
                    utc=row['utc']
                    et=sp.utc2et(utc[:-1])
                    state,_=sp.spkcpo(body.upper(),et,'MOON_ME','OBSERVER','LT+S',obs,'MOON','MOON_ME')
                    vec=np.array(state[:3]);vec/=np.linalg.norm(vec)
                    az=math.degrees(math.atan2(float(vec@east),float(vec@north)))%360
                    el=math.degrees(math.asin(float(vec@up)))
                    delta_az=(az-row['az_deg']+180)%360-180
                    diffs.append([delta_az,el-row['el_deg']])
                errs=np.array(diffs)
                scores.append({'site':key,'body':body,'n':len(errs),'rmse_az_deg':float(np.sqrt(np.mean(errs[:,0]**2))),'rmse_el_deg':float(np.sqrt(np.mean(errs[:,1]**2))),'max_abs_error_deg':float(np.max(np.abs(errs)))})
        return {'method':'independent SPICE vs bundled Horizons observer samples','comparisons':scores,'total_samples':sum(s['n'] for s in scores)}
    finally:sp.kclear()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');args=parser.parse_args()
    result=validate(download_kernels(BASE/'data'/'cache'/'naif',args.download))
    print(json.dumps(result,indent=2))
    assert all(x['max_abs_error_deg']<0.001 for x in result['comparisons']),'SPICE/Horizons geometry deviation exceeded 0.001 deg'
