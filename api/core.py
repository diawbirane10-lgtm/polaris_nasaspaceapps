"""POLARIS 2026: reproducible lunar mission feasibility calculations.

Scientific boundary: JPL Horizons apparent Sun/Earth azimuth/elevation at a
selenographic observing site, **without terrain shadowing**. No radio link budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import math
import re
from typing import Any

import requests

from .horizon import HorizonProfile, solar_disk_visible_fraction

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_DATE_RE = re.compile(r"^\s*(\d{4}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)")

@dataclass(frozen=True)
class Site:
    label: str
    lat: float
    lon_e: float
    height_km: float = 0.0

    def __post_init__(self):
        if not -90 <= self.lat <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not 0 <= self.lon_e < 360:
            raise ValueError("East longitude must be in [0, 360) degrees")
        if not -5 <= self.height_km <= 20:
            raise ValueError("Height out of demo bounds")


def horizons_params(body: str, site: Site, start: str, days: int, step_hours: int) -> dict:
    if body not in ("10", "399"):
        raise ValueError("Only Sun 10 and Earth 399 are supported")
    dt = datetime.strptime(start, "%Y-%m-%d")
    if not 1 <= days <= 14 or step_hours not in (1, 2, 3, 4, 6, 12):
        raise ValueError("days 1..14 and step hours 1/2/3/4/6/12 only")
    return {
        "format": "json", "COMMAND": f"'{body}'", "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'", "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@301'", "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{site.lon_e:.6f},{site.lat:.6f},{site.height_km:.5f}'",
        "START_TIME": f"'{dt:%Y-%m-%d}'",
        "STOP_TIME": f"'{dt + timedelta(days=days):%Y-%m-%d}'",
        "STEP_SIZE": f"'{step_hours} h'", "QUANTITIES": "'4'",
        "TIME_TYPE": "'UT'", "ANG_FORMAT": "'DEG'", "EXTRA_PREC": "'YES'", "APPARENT": "'AIRLESS'",
    }


def parse_horizons(text: str) -> list[dict[str, Any]]:
    """Extract azimuth/elevation from a Horizons QUANTITIES=4 observer table.

    QUANTITIES=4 produces azimuth and elevation as the final two numerical
    columns. Rows with missing data (n.a., etc.) are rejected instead of
    silently substituting a value. UTC calendar timestamps are preserved.
    """
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ValueError("Horizons response has no ephemeris table")
    block = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = []
    for line in block.splitlines():
        match = _DATE_RE.match(line)
        if not match:
            continue
        date = match.group(1)
        remainder = line[match.end():].strip()
        # 'm', '*', and a trailing comma can occur in Horizons observer output.
        values = re.findall(r"(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?(?![\w.])", remainder)
        if len(values) < 2:
            continue
        az, el = map(float, values[-2:])
        if not (0 <= az <= 360 and -90 <= el <= 90):
            raise ValueError(f"Invalid Horizons azimuth/elevation: {az}, {el}")
        stamp = datetime.strptime(date, "%Y-%b-%d %H:%M" if len(date) == 17 else "%Y-%b-%d %H:%M:%S")
        rows.append({"utc": stamp.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                     "az_deg": round(az, 6), "el_deg": round(el, 6)})
    if not rows:
        raise ValueError("No valid azimuth/elevation records found in Horizons output")
    return rows


@lru_cache(maxsize=128)
def get_ephemeris(body: str, site: Site, start: str, days: int, step_hours: int) -> list[dict]:
    params = horizons_params(body, site, start, days, step_hours)
    response = requests.get(HORIZONS_URL, params=params, timeout=(6, 24), headers={"User-Agent": "POLARIS-SpaceApps-2026/0.1 research hackathon"})
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", "")
    if payload.get("error"):
        raise ValueError(str(payload["error"])[:280])
    return parse_horizons(result)


def mission_metrics(sun: list[dict], earth: list[dict], step_hours: int,
                    pv_area_m2: float = 16.0, pv_efficiency: float = 0.28,
                    pv_derate: float = 0.78, load_w: float = 400.0,
                    battery_kwh: float = 20.0, initial_soc: float = 0.8,
                    array_mode: str = "horizontal",
                    skyline: HorizonProfile | None = None) -> dict[str, Any]:
    """Time-integrated horizon and energy estimates, explicitly non-flight-qualified.

    Each ephemeris row is a LEFT_ENDPOINT sample for the interval that follows.
    Final row is a boundary observation; it contributes zero duration. This
    avoids incorrectly reporting 14-day windows as 14 days + 1 sample.
    An optional externally provenance-tracked skyline may occlude Sun/Earth.
    Without skyline the model explicitly uses the flat/geometric 0-deg horizon.
    """
    if array_mode not in ("horizontal", "tracking"):
        raise ValueError("Invalid panel mode")
    if step_hours not in (1, 2, 3, 4, 6, 12):
        raise ValueError("Invalid sampling step")
    if not all(math.isfinite(x) for x in (pv_area_m2, pv_efficiency, pv_derate,
                                          load_w, battery_kwh, initial_soc)):
        raise ValueError("Nonfinite energy parameter")
    if not (pv_area_m2 > 0 and 0 < pv_efficiency <= 1 and 0 < pv_derate <= 1
            and load_w >= 0 and battery_kwh > 0 and 0 <= initial_soc <= 1):
        raise ValueError("Invalid energy parameters")
    sun_by_time = {r["utc"]:r for r in sun}
    earth_by_time = {r["utc"]:r for r in earth}
    if len(sun_by_time) != len(sun) or len(earth_by_time) != len(earth):
        raise ValueError("Duplicate ephemeris epochs")
    if set(sun_by_time) != set(earth_by_time) or len(sun_by_time) < 2:
        raise ValueError("Sun and Earth require matching UTC epochs and at least 2 samples")
    for row in (*sun, *earth):
        if not all(math.isfinite(row[field]) for field in ("az_deg", "el_deg")):
            raise ValueError("Nonfinite ephemeris angles")
    ordered_times = sorted(sun_by_time)
    results = []
    soc_kwh = initial_soc * battery_kwh
    min_soc = initial_soc
    unmet_kwh = 0.0
    max_dark_h = dark_h = 0.0
    max_earth_gap_h = earth_gap_h = 0.0
    sun_hours = earth_hours = total_hours = 0.0
    for idx, utc in enumerate(ordered_times):
        row = sun_by_time[utc]
        earth_row = earth_by_time[utc]
        sun_el, earth_el = row["el_deg"], earth_row["el_deg"]
        sun_h = skyline.elevation(row["az_deg"]) if skyline else 0.0
        earth_h = skyline.elevation(earth_row["az_deg"]) if skyline else 0.0
        sun_margin = sun_el - sun_h
        earth_margin = earth_el - earth_h
        solar_frac = solar_disk_visible_fraction(sun_margin)
        sun_visible = solar_frac > 0
        earth_visible = earth_margin > 0
        factor = (1.0 if array_mode == "tracking" else max(0, math.sin(math.radians(sun_el))))
        pv_w = 1361.0 * pv_area_m2 * pv_efficiency * pv_derate * factor * solar_frac
        hours = ((datetime.fromisoformat(ordered_times[idx + 1].replace("Z", "+00:00"))
                  - datetime.fromisoformat(utc.replace("Z", "+00:00"))).total_seconds() / 3600
                 if idx + 1 < len(ordered_times) else 0)
        if not 0 <= hours <= step_hours + 0.001:
            raise ValueError("Irregular or invalid ephemeris sampling interval")
        total_hours += hours
        sun_hours += hours if sun_visible else 0
        earth_hours += hours if earth_visible else 0
        net_energy_kwh = (pv_w-load_w) * hours/1000
        proposed_kwh = soc_kwh + net_energy_kwh
        if proposed_kwh < 0:
            unmet_kwh += -proposed_kwh
        soc_kwh = min(battery_kwh, max(0.0, proposed_kwh))
        min_soc = min(min_soc, soc_kwh / battery_kwh)
        dark_h = dark_h + hours if not sun_visible else 0
        earth_gap_h = earth_gap_h + hours if not earth_visible else 0
        max_dark_h = max(max_dark_h, dark_h)
        max_earth_gap_h = max(max_earth_gap_h, earth_gap_h)
        results.append({"utc": utc, "sun_az": row["az_deg"],
                        "sun_el": sun_el, "earth_az": earth_row["az_deg"],
                        "earth_el": earth_el, "sun_horizon_deg": round(sun_h, 4),
                        "earth_horizon_deg": round(earth_h, 4),
                        "sun_margin_deg": round(sun_margin, 4),
                        "earth_margin_deg": round(earth_margin, 4),
                        "sun_disk_visible_pct": round(solar_frac*100, 2),
                        "sun_visible": sun_visible, "earth_visible": earth_visible,
                        "pv_w": round(pv_w, 2), "soc": round(soc_kwh / battery_kwh, 4),
                        "sample_hours": hours})
    if total_hours <= 0:
        raise ValueError("Ephemeris time span must have positive duration")
    return {"samples": results, "summary": {
        "sun_visible_pct": round(100 * sun_hours / total_hours, 2),
        "earth_visible_pct": round(100 * earth_hours / total_hours, 2),
        "earth_local_clear_upper_bound_pct": round(100 * earth_hours / total_hours, 2),
        "earth_obstructed_by_local_terrain_pct": round(100 * (total_hours-earth_hours) / total_hours, 2),
        "sun_local_clear_upper_bound_pct": round(100 * sun_hours / total_hours, 2),
        "sun_visible_hours": round(sun_hours, 2),
        "earth_visible_hours": round(earth_hours, 2),
        "max_dark_hours": round(max_dark_h, 2),
        "max_earth_gap_hours": round(max_earth_gap_h, 2),
        "min_soc_pct": round(100 * min_soc, 2),
        "unserved_energy_kwh": round(unmet_kwh, 3),
        "last_soc_pct": round(100 * results[-1]["soc"], 2),
        "duration_hours": round(total_hours, 2),
        "horizon_model": "DEM-profile" if skyline else "geometric-zero-degree",
        "n_samples": len(results)}}
