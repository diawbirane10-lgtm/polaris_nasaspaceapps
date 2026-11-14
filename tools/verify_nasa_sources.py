#!/usr/bin/env python3
"""Download/authenticate original NASA LOLA source DEMs and audit POLARIS profiles.

Requires: pip install rasterio pyproj numpy requests. An outbound HTTPS connection is
required. The checked-in small JSON reference is derived from these 40 MB NASA files.
Use --download to retrieve GeoTIFFs, --verify-profiles to recompute skylines.
"""
import argparse
import hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from api.nasa_reference import load_dataset
from tools.prepare_lola_horizon import create_profile


def download_checked(url: str, sha256: str, path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix('.part')
        try:
            with requests.get(url,timeout=(8,120),stream=True) as resp:
                resp.raise_for_status()
                with tmp.open('wb') as out:
                    for chunk in resp.iter_content(2*1024*1024):
                        if chunk:out.write(chunk)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    actual=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    if actual!=sha256:
        raise RuntimeError(f'NASA file digest mismatch: {path.name}; expected {sha256}, got {actual}')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--verify-profiles',action='store_true')
    parser.add_argument('--dir',type=Path,default=Path('data/nasa/original_dems'))
    args=parser.parse_args()
    if not args.download and not args.verify_profiles:
        parser.error('Choose --download and/or --verify-profiles')
    data=load_dataset()
    for key,site in data['sites'].items():
        path=args.dir / f'{key}_lola_5m.tif'
        if args.download:
            download_checked(site['dem_url'],site['dem_sha256'],path)
        if args.verify_profiles:
            if not path.is_file(): raise RuntimeError(f'Missing {path}; run --download')
            p=create_profile(str(path),site['lat_deg'],site['lon_e_deg'],2.0,6.0,5.0,50.0)
            gold=site['horizon_profile']['elevations_deg']
            diffs=[abs(a-b) for a,b in zip(p['elevations_deg'],gold)]
            print(f'{key}: max horizon difference {max(diffs):.4f}deg')
            if max(diffs)>0.15:
                raise RuntimeError('DEM profile changed beyond 0.15deg tolerance; inspect projection and frames')
        print(f'{key}: provenance verified' if args.download else f'{key}: profile checked')

if __name__=='__main__': main()
