import math
import pytest
from api.core import mission_metrics
from api.decision import counterfactual

def sample_rows():
    a = [
        {'utc':'2026-11-14T00:00Z','az_deg':0.0,'el_deg':5.0},
        {'utc':'2026-11-14T06:00Z','az_deg':90.0,'el_deg':5.0},
    ]
    return a, [{**x, 'az_deg':180.0, 'el_deg':-5.0} for x in a]

@pytest.mark.parametrize('bad', [math.nan, math.inf, -math.inf])
def test_energy_reject_nonfinite(bad):
    sun, earth = sample_rows()
    with pytest.raises(ValueError, match='Nonfinite'):
        mission_metrics(sun, earth,6,pv_area_m2=bad)

@pytest.mark.parametrize('bad', [math.nan, math.inf])
def test_azimuth_reject_nonfinite(bad):
    sun, earth = sample_rows()
    sun[0]['az_deg'] = bad
    with pytest.raises(ValueError, match='Nonfinite'):
        mission_metrics(sun,earth,6)

def test_counterfactual_rejects_nonfinite():
    with pytest.raises(ValueError, match='Nonfinite'):
        counterfactual(load_w=math.nan)

def test_exact_duration_ignores_boundary_sample():
    sun, earth = sample_rows()
    result=mission_metrics(sun,earth,6)
    assert result['summary']['duration_hours']==6
    assert result['summary']['sun_visible_hours']==6
    assert result['summary']['earth_visible_hours']==0

def test_hourly_audit_contains_science_qualifiers():
    import json
    from pathlib import Path
    audit=json.loads((Path(__file__).parents[1]/'data/analysis/hourly_sampling_audit_2026-11-14.json').read_text())
    s=next(r for r in audit['results'] if r['site']=='shackleton_rim' and '2026-11-16' in r['window_utc'][0])
    assert s['one_hour_local_earth_clear_h'] == 21
    assert s['six_hour_local_earth_clear_h'] == 18
    assert audit['limitations']
