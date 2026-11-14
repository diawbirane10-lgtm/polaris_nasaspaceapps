#!/usr/bin/env python3
"""Export JPL/LOLA-derived counterfactual evidence (offline; no network).

Run from project root: python tools/export_counterfactual.py
"""
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from api.decision import counterfactual

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'data'/'analysis'

def main():
    DEST.mkdir(exist_ok=True,parents=True)
    report=[]
    rows=[]
    for site in ('connecting_ridge','shackleton_rim'):
        for start in ('2026-11-14T00:00Z','2026-11-14T12:00Z',
                      '2026-11-14T18:00Z','2026-11-15T00:00Z'):
            result=counterfactual(site_key=site,start_utc=start,duration_hours=24,delay_hours=48)
            report.append(result)
            for name,scenario in result['scenarios'].items():
                s=scenario['summary']
                rows.append({'baseline_site':site,'baseline_start':start,'scenario':name,
                             'site':scenario['site_key'],'start_utc':scenario['start_utc'],
                             'local_earth_clear_upper_bound_hours':s['earth_visible_hours'],
                             'local_sun_clear_upper_bound_hours':s['sun_visible_hours'],
                             'max_sampled_local_earth_gap_h':s['max_earth_gap_hours'],
                             'model_min_soc_pct':s['min_soc_pct'],
                             'unserved_kwh':s['unserved_energy_kwh'],
                             'NASA_data_sha256':result['dataset_sha256']})
    (DEST/'replanning_evidence_v0.4.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    with (DEST/'replanning_matrix_v0.4.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(f'Wrote {len(report)} reproducible NASA-sourced comparisons, {len(rows)} scenario rows')

if __name__=='__main__':main()
