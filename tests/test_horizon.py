"""Synthetic fixtures only. No terrain is falsely attributed to NASA."""
import math
import pytest
from api.horizon import HorizonProfile, ray_elevation_deg, horizon_from_rays, solar_disk_visible_fraction
from api.core import mission_metrics


def _s(els,azs=None):
    if azs is None:azs=[0]*len(els)
    return [{'utc':f'2026-11-14T{i:02d}:00:00Z','az_deg':az,'el_deg':el} for i,(el,az) in enumerate(zip(els,azs))]


def test_ray_curvature_is_below_tangent_for_equal_heights():
    assert ray_elevation_deg(20000, 0, 0) < 0
    assert -0.5 < ray_elevation_deg(20000, 0, 0) < -0.2


def test_horizon_elevation_and_seam_interpolation():
    h=HorizonProfile((0,10,0,20),'SYNTHETIC: hand-authored test skyline')
    assert h.elevation(90)==10
    assert h.elevation(45)==5
    assert h.elevation(315)==10
    assert h.elevation(360)==0
    assert h.elevation(-45)==10


def test_horizon_rejects_missing_dem_ray():
    with pytest.raises(ValueError,match='Missing DEM ray'):
        horizon_from_rays([[(100,0)],[(100,0)],[],[(100,0)]],0,'Synthetic')


def test_solar_disk_partial_visibility():
    assert solar_disk_visible_fraction(0)==pytest.approx(0.5)
    assert solar_disk_visible_fraction(-1)==0
    assert solar_disk_visible_fraction(1)==1


def test_terrain_can_occlude_earth_and_sun():
    h=HorizonProfile((5,5,5,5),'SYNTHETIC: flat positive skyline')
    a=mission_metrics(_s([3,8,8]),_s([3,3,3]),1,skyline=h)
    assert a['summary']['horizon_model']=='DEM-profile'
    assert a['summary']['sun_visible_pct']==50
    assert a['summary']['earth_visible_pct']==0
    assert a['summary']['max_dark_hours']==1


def test_time_weighted_visibility_excludes_terminal_sample():
    # Exactly 2 intervals. Last endpoint must not inflate sunlight fraction.
    sun=_s([1,1,-10]); earth=_s([1,1,1])
    a=mission_metrics(sun,earth,1)
    assert a['summary']['sun_visible_pct']==100
    assert a['summary']['duration_hours']==2
    assert a['summary']['sun_visible_hours']==2


def test_misaligned_sun_earth_fails():
    with pytest.raises(ValueError,match='matching UTC'):
        mission_metrics(_s([1,1,1]),_s([1,1]),1)
