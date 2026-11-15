"""FastAPI adapter to JPL Horizons, served locally or on Vercel."""
from __future__ import annotations

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from requests.exceptions import RequestException

try:
    from .core import Site, get_ephemeris, mission_metrics
    from .nasa_reference import analyze_reference, load_dataset
    from .decision import counterfactual
    from .report import build_report_data, latex_source, make_pdf
    from .copilot import CopilotRequest, analyze
    from .review import MissionReviewRequest, build_review
    from .review_pdf import make_decision_pdf, latex_decision_report
except ImportError:
    from api.core import Site, get_ephemeris, mission_metrics
    from api.nasa_reference import analyze_reference, load_dataset
    from api.decision import counterfactual
    from api.report import build_report_data, latex_source, make_pdf
    from api.copilot import CopilotRequest, analyze
    from api.review import MissionReviewRequest, build_review
    from api.review_pdf import make_decision_pdf, latex_decision_report

app = FastAPI(title="POLARIS lunar mission navigator", version="2.0.0-prototype")
# NASA prototype mode: private account/approval routers intentionally not mounted.
# Existing Supabase data and its RLS policies are left intact and inaccessible here.
BASE = Path(__file__).resolve().parent.parent

@app.get('/workspace')
@app.get('/workspace.html')
@app.get('/admin')
def prototype_entry():
    # Legacy links now land in the same eight-page public mission control.
    return FileResponse(BASE/'public'/'index.html',headers={'Cache-Control':'no-cache'})

@app.get('/api/health')
def health():
    return {"status": "ok", "service": "POLARIS", "ephemerides": "Live JPL Horizons requests (unvalidated from this environment)", "model": "NASA LOLA demo: 6km terrain horizon on /api/nasa-reference; other sites: geometric 0-degree horizon"}

@app.get('/api/nasa-sites')
def nasa_sites():
    data=load_dataset()
    return {'source_type':'nasa_real_reference', 'sites':[
        {'key':key,'name':site['name'],'lat_deg':site['lat_deg'],
         'lon_e_deg':site['lon_e_deg'],'dem_height_m':site['dem_height_m']}
        for key,site in data['sites'].items()],
        'start_utc':data['start_utc'],'end_utc':data['end_utc'],
        'limitations':[data['science_warning'],data['terrain']['horizontal_extent']]}

@app.get('/api/nasa-reference/{site_key}')
def nasa_reference(site_key: str,
                   area: float=Query(16,gt=0,le=200),
                   load: float=Query(400,ge=0,le=100000),
                   battery: float=Query(20,gt=0,le=10000),
                   mode: str=Query('horizontal')):
    if site_key not in load_dataset()['sites']:
        raise HTTPException(status_code=404, detail='Unknown NASA reference site')
    try:
        return analyze_reference(site_key,area=area,load=load,battery=battery,mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))


@app.get('/api/replan')
def replan(site: str=Query('connecting_ridge'),
           start: str=Query('2026-11-14T00:00Z'),
           hours: int=Query(24), delay: int=Query(48),
           area: float=Query(16, gt=0, le=200),
           load: float=Query(400, ge=0, le=100000),
           battery: float=Query(20, gt=0, le=10000),
           mode: str=Query('horizontal')):
    try:
        return counterfactual(site_key=site,start_utc=start,
                              duration_hours=hours,delay_hours=delay,
                              pv_area_m2=area,load_w=load,battery_kwh=battery,mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))


@app.get('/api/copilot/status')
def copilot_status():
    provider = os.environ.get('POLARIS_LLM_PROVIDER','groq').lower()
    available = (provider == 'kilo' or (
        bool(os.environ.get('POLARIS_LLM_API_KEY','').strip()) and provider in ('groq','huggingface')))
    return {'model_connected':available, 'provider':provider if available else None,
            'provider_configured':available, 'live_provider_health_verified':False,
            'free_text_enabled':True,
            'language_support':'multilingual; Python fallback when model unavailable',
            'simulation_tool':'python', 'evidence':'JPL Horizons and LOLA',
            'external_data_notice': 'LLM prompts may be processed or logged by third-party providers; do not enter confidential information.' if provider=='kilo' else None}

@app.post('/api/copilot')
def mission_copilot(request: CopilotRequest):
    try:
        return analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)[:220])

@app.post('/api/mission-report.pdf')
def mission_report_pdf(request: CopilotRequest):
    """Recompute scenario tables and downloadable technical PDF on demand."""
    try:
        report = build_report_data(request)
        pdf, renderer = make_pdf(report, prefer_latex=False)  # portable serverless PDF
        return Response(content=pdf, media_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="POLARIS_{report["report_id"]}.pdf"',
            'X-POLARIS-REPORT-ID': report['report_id'],
            'X-POLARIS-RENDERER': 'reportlab',
        })
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)[:260])

@app.post('/api/mission-report.tex')
def mission_report_tex(request: CopilotRequest):
    """Download the exact XeLaTeX scientific report source using Libertinus Serif."""
    try:
        report=build_report_data(request)
        return Response(content=latex_source(report).encode('utf-8'), media_type='text/x-tex', headers={
            'Content-Disposition':f'attachment; filename="POLARIS_{report["report_id"]}.tex"',
            'X-POLARIS-REPORT-ID':report['report_id'],
        })
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)[:260])

@app.post('/api/mission-report.json')
def mission_report_json(request: CopilotRequest):
    try:return build_report_data(request)
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)[:260])

@app.post('/api/mission-review')
def mission_review(request: MissionReviewRequest):
    """Review the currently requested mission against real computed requirements."""
    try:
        return build_review(request)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)[:300])


@app.post('/api/mission-decision/{kind}.{fmt}')
def mission_decision_package(kind: str, fmt: str, request: MissionReviewRequest):
    """On-demand decision packages. Never accept browser-supplied simulation results."""
    if kind not in ('brief','dossier') or fmt not in ('pdf','tex','json'):
        raise HTTPException(status_code=404, detail='Unknown decision package')
    try:
        data=build_review(request)
        if fmt=='json':return data
        if fmt=='tex':
            payload=latex_decision_report(data,kind).encode('utf-8')
            mime='application/x-tex';renderer='xelatex-source'
        else:
            payload,renderer=make_decision_pdf(data,kind,prefer_latex=False)
            mime='application/pdf'
        return Response(content=payload,media_type=mime,headers={
            'Content-Disposition':f'attachment; filename="POLARIS_{data["review_id"]}_{kind}.{fmt}"',
            'X-POLARIS-REVIEW-ID':data['review_id'],'X-POLARIS-RENDERER':renderer,
        })
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)[:300])


@app.get('/api/science-sources')
def science_sources():
    import json
    return json.loads((BASE/'data'/'analysis'/'source_catalog.json').read_text(encoding='utf-8'))

@app.get('/api/spice-validation')
def spice_validation():
    import json
    return json.loads((BASE/'data'/'analysis'/'spice_crosscheck_2026-11-14.json').read_text(encoding='utf-8'))

@app.get('/api/mission')
def mission(lat: float = Query(-89.5, ge=-90, le=-80), lon: float = Query(0, ge=0, lt=360),
            start: str = Query('2026-11-14'), days: int = Query(5, ge=1, le=14),
            step: int = Query(6), area: float = Query(16, gt=0, le=200),
            load: float = Query(400, ge=0, le=100000),
            battery: float = Query(20, gt=0, le=10000),
            mode: str = Query('horizontal')):
    try:
        datetime.strptime(start, "%Y-%m-%d")
        site = Site(label='Custom observer', lat=lat, lon_e=lon)
        # Independent NASA requests run concurrently to reduce latency.
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_sun = pool.submit(get_ephemeris, '10', site, start, days, step)
            future_earth = pool.submit(get_ephemeris, '399', site, start, days, step)
            sun, earth = future_sun.result(), future_earth.result()
        output = mission_metrics(sun, earth, step, pv_area_m2=area, load_w=load,
                                battery_kwh=battery, array_mode=mode)
        return {"site": {"lat_deg":lat, "lon_e_deg":lon, "height_km":0},
                "start_utc":start, "duration_days":days, "step_hours":step,
                "source": "JPL Horizons API, QUANTITIES=4, CENTER=coord@301",
                "model": "geometric horizon only; terrain not yet included",
                "assumptions": {"pv_efficiency":0.28,"pv_derate":0.78,"solar_constant_w_m2":1361,
                                "pv_area_m2":area,"panel_mode":mode,"load_w":load,"battery_kwh":battery,
                                "initial_soc_pct":80, "no_terrain":True,"no_radio_link_budget":True}, **output}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Input or ephemeris error: {str(exc)[:320]}")
    except RequestException as exc:
        raise HTTPException(status_code=503, detail=f"JPL Horizons unavailable: {str(exc)[:320]}")

# Hosting public assets locally; Vercel also serves public/ directly.
if (BASE/'public').exists():
    app.mount('/assets', StaticFiles(directory=str(BASE/'public')), name='assets')

@app.get('/')
def homepage():
    return FileResponse(BASE/'public'/'index.html')

@app.get('/demo')
def public_demo():
    return FileResponse(BASE/'public'/'index.html')

@app.get('/api/skyline/{site_key}')
def skyline(site_key: str):
    """Expose the provenance-tracked NASA LOLA 6 km local skyline for UI plots."""
    source = load_dataset()['sites'].get(site_key)
    if source is None:
        raise HTTPException(status_code=404,detail='Unknown NASA reference site')
    return {
        'site_key':site_key,
        'name':source['name'],
        'profile':source['horizon_profile'],
        'observer_mast_m':source['observer_height_above_surface_m'],
        'radius_km':source['horizon_profile']['max_range_km'],
        'source':{'dem_url':source['dem_url'],'sha256':source['dem_sha256']},
        'limitations':'Only 6 km nearby terrain is represented. Far-terrain occlusion unknown.'
    }

@app.get('/api/science-audit')
def science_audit():
    """Externally repeated JPL cadence comparison; not a flight-system claim."""
    import json
    return json.loads((BASE/'data'/'analysis'/'hourly_sampling_audit_2026-11-14.json').read_text(encoding='utf-8'))
