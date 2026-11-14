"""POLARIS horizon geometry, independent of the ephemerides source.

No arbitrary site horizon is claimed to be an observed NASA profile.
A profile must be computed from actual georeferenced lunar DEM heights with
an audited mapping between local azimuth and DEM coordinates.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

MOON_MEAN_RADIUS_M = 1_737_400.0


@dataclass(frozen=True)
class HorizonProfile:
    """Uniform, periodic 0..360 deg compass horizon; 0=N, 90=E.

    elevations_deg[i] belongs to azimuth 360*i/len(elevations_deg).
    The observer's height (antenna/mast) must have been included in the
    source profile's construction.
    """
    elevations_deg: tuple[float, ...]
    provenance: str

    def __post_init__(self):
        if len(self.elevations_deg) < 4:
            raise ValueError('A horizon profile needs >=4 azimuth bins')
        if not self.provenance.strip():
            raise ValueError('Horizon profile needs source provenance')
        if any(not math.isfinite(x) or not -90 <= x <= 90 for x in self.elevations_deg):
            raise ValueError('Invalid or nonfinite horizon elevation')

    def elevation(self, azimuth_deg: float) -> float:
        """Continuous angular interpolation, including the 359 -> 0 seam."""
        if not math.isfinite(azimuth_deg):
            raise ValueError('Invalid azimuth')
        n = len(self.elevations_deg)
        ix = (azimuth_deg % 360.0) * n / 360.0
        a = math.floor(ix)
        t = ix - a
        return (1.0 - t) * self.elevations_deg[a % n] + t * self.elevations_deg[(a + 1) % n]


def ray_elevation_deg(distance_m: float, target_height_m: float,
                      observer_height_m: float,
                      radius_m: float = MOON_MEAN_RADIUS_M) -> float:
    """Exact spherical ray geometry from an observer to a surface point.

    The distance is surface *arc* length; both heights reference the same
    lunar datum. This accounts for curvature instead of flat-ground atan(dh/d).
    """
    if not all(math.isfinite(x) for x in (distance_m,target_height_m,observer_height_m,radius_m)):
        raise ValueError('Nonfinite ray geometry')
    if distance_m <= 0 or radius_m <= 0 or radius_m + min(target_height_m,observer_height_m) <= 0:
        raise ValueError('Invalid ray geometry')
    theta = distance_m / radius_m
    if theta <= 0 or theta >= math.pi:
        raise ValueError('Ray must be within lunar half circumference')
    horizontal = (radius_m + target_height_m) * math.sin(theta)
    vertical = (radius_m + target_height_m) * math.cos(theta) - (radius_m + observer_height_m)
    return math.degrees(math.atan2(vertical, horizontal))


def horizon_from_rays(rays: list[list[tuple[float, float]]],
                      observer_height_m: float, provenance: str,
                      radius_m: float = MOON_MEAN_RADIUS_M) -> HorizonProfile:
    """Construct skyline from DEM-derived radial samples by azimuth bin.

    Each ray contains (arc_distance_m, DEM_height_m) pairs. It is the caller's
    responsibility to prepare real radial heights and trace their coordinates.
    Empty rays are an error: missing terrain must not turn into clear sight.
    """
    result = []
    for ray in rays:
        if not ray:
            raise ValueError('Missing DEM ray cannot imply clear visibility')
        result.append(max(ray_elevation_deg(d, z, observer_height_m, radius_m) for d,z in ray))
    return HorizonProfile(tuple(result), provenance)


def solar_disk_visible_fraction(margin_deg: float, apparent_radius_deg: float = 0.2666) -> float:
    """Approximate illuminated fraction of a uniform solar disk vs flat skyline.

    This is a local straight-line skyline approximation; no terrain parallax,
    physical limb darkening, panel attitude, or thermal feedback.
    """
    if not math.isfinite(margin_deg) or apparent_radius_deg <= 0:
        raise ValueError('Invalid solar geometry')
    x = margin_deg / apparent_radius_deg
    if x <= -1: return 0.0
    if x >= 1: return 1.0
    return (math.acos(-x) + x*math.sqrt(1-x*x)) / math.pi
