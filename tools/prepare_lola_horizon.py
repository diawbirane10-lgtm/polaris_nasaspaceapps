#!/usr/bin/env python3
"""Offline NASA LOLA DEM to POLARIS horizon profile converter.

Installation (NOT needed for web API): pip install rasterio pyproj
Input: genuine NASA south-polar GeoTIFF with a valid lunar polar CRS.
Output: JSON horizon, one elevation angle per azimuth, with provenance.

IMPORTANT: To avoid falsely treating off-tile terrain as a clear horizon, rays
that exit the DEM earlier than requested max_distance abort instead of filling
with zero. Use an appropriate wide-area NASA mosaic or a smaller honest radius.
For long lunar shadows (dozens of km), local tiles are often insufficient.
"""
import argparse
import json
import math
from pathlib import Path

from api.horizon import MOON_MEAN_RADIUS_M, horizon_from_rays


def project_lunar_site(ds, latitude: float, longitude_e: float):
    import pyproj
    source_crs = pyproj.CRS.from_proj4(
        f'+proj=longlat +a={MOON_MEAN_RADIUS_M} +b={MOON_MEAN_RADIUS_M} +no_defs')
    if ds.crs is None:
        raise ValueError('DEM has no CRS. Define its validated lunar stereographic CRS first.')
    to_map = pyproj.Transformer.from_crs(source_crs, ds.crs, always_xy=True)
    x0, y0 = to_map.transform(longitude_e, latitude)
    eps = 0.0001
    if latitude + eps > 90:
        raise ValueError('Finite difference fails at the north pole')
    xe, ye = to_map.transform(longitude_e + eps, latitude)
    xn, yn = to_map.transform(longitude_e, latitude + eps)
    dx_e, dy_e = xe-x0, ye-y0
    dx_n, dy_n = xn-x0, yn-y0
    en = math.hypot(dx_e, dy_e)
    nn = math.hypot(dx_n, dy_n)
    if min(en,nn) <= 1e-9:
        raise ValueError('Degenerate projected azimuth mapping')
    east = (dx_e/en,dy_e/en)
    north = (dx_n/nn,dy_n/nn)
    if abs(east[0]*north[0] + east[1]*north[1]) > 0.05:
        raise ValueError('Non-orthogonal local grid; inspect projection and CRS')
    # Jacobian gives the local map scale relative to arc length on Moon.
    map_scale_e = en / (MOON_MEAN_RADIUS_M*math.cos(math.radians(latitude))*math.radians(eps))
    map_scale_n = nn / (MOON_MEAN_RADIUS_M*math.radians(eps))
    scale = (map_scale_e + map_scale_n) / 2
    if not 0.85 < scale < 1.3:
        raise ValueError('Unexpected map scale; validate lunar CRS')
    return x0, y0, east, north, scale


def create_profile(path: str, latitude: float, longitude_e: float, mast_m: float,
                   radius_km: float = 20.0, angular_step_deg: float = 2.0,
                   radial_step_m: float = 50.0):
    import rasterio
    import numpy as np
    if angular_step_deg <= 0 or 360 / angular_step_deg != int(360 / angular_step_deg):
        raise ValueError('Azimuth step must evenly divide 360')
    if radial_step_m <= 0 or radius_km <= 0:
        raise ValueError('Nonpositive sampling range')
    with rasterio.open(path) as ds:
        if ds.count < 1:
            raise ValueError('No DEM band')
        x0,y0,east,north,scale=project_lunar_site(ds,latitude,longitude_e)
        z0 = float(next(ds.sample([(x0,y0)],masked=True))[0])
        if not math.isfinite(z0) or (ds.nodata is not None and z0==ds.nodata):
            raise ValueError('Observing site lies outside valid DEM')
        rays=[]
        angles=[angular_step_deg*i for i in range(int(360/angular_step_deg))]
        steps=math.ceil(radius_km*1000/radial_step_m)
        for az in angles:
            rad=math.radians(az)
            direction=(east[0]*math.sin(rad)+north[0]*math.cos(rad),
                       east[1]*math.sin(rad)+north[1]*math.cos(rad))
            distances=[min((i+1)*radial_step_m,radius_km*1000) for i in range(steps)]
            coords=[(x0 + d*scale*direction[0], y0+d*scale*direction[1]) for d in distances]
            samples=list(ds.sample(coords,masked=True))
            if any(bool(np.ma.getmaskarray(s)[0]) for s in samples):
                raise ValueError(f'Missing DEM coverage at azimuth {az:.1f} deg within {radius_km} km')
            if ds.nodata is not None and any(float(s[0])==ds.nodata for s in samples):
                raise ValueError(f'DEM nodata on ray {az:.1f} deg')
            if any(not math.isfinite(float(s[0])) for s in samples):
                raise ValueError('Nonfinite DEM height')
            rays.append(list(zip(distances,[float(s[0]) for s in samples])))
        provenance=(f'{Path(path).name}; lat={latitude}; east_lon={longitude_e}; '
                    f'radius_km={radius_km}; step_m={radial_step_m}; '
                    f'angular_deg={angular_step_deg}; mast_m={mast_m}; '
                    f'CRS={ds.crs}; lunar-radius={MOON_MEAN_RADIUS_M}')
        profile=horizon_from_rays(rays,z0+mast_m,provenance)
        return {'azimuth_zero':'north', 'azimuth_positive':'east',
                'source':'NASA LOLA DEM (provided by operator; validate source before use)',
                'site':{'lat_deg':latitude,'lon_e_deg':longitude_e,'dem_height_m':z0,'mast_m':mast_m},
                'radius_km':radius_km,'azimuth_resolution_deg':angular_step_deg,
                'provenance':provenance, 'elevations_deg':list(profile.elevations_deg)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dem',required=True)
    p.add_argument('--lat',type=float,required=True)
    p.add_argument('--lon',type=float,required=True)
    p.add_argument('--mast-m',type=float,default=2.0)
    p.add_argument('--radius-km',type=float,default=20.0)
    p.add_argument('--angular-step-deg',type=float,default=2.0)
    p.add_argument('--radial-step-m',type=float,default=50.0)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    prof=create_profile(a.dem,a.lat,a.lon,a.mast_m,a.radius_km,
                        a.angular_step_deg,a.radial_step_m)
    Path(a.output).write_text(json.dumps(prof,indent=2))
    print('Saved horizon profile:',a.output)
