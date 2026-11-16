"""Regression tests: current public POLARIS emblem and submission-facing copy.

The image assertion checks the actual generated PDFs, not only source references.
"""
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

from api.index import app
from api.branding import LOGO_FILE

client = TestClient(app)

PARAMS = {
    "question": "Explain the energy shortfall",
    "site": "connecting_ridge",
    "start": "2026-11-14T00:00Z",
    "duration_hours": 24,
    "delay_hours": 48,
    "pv_area_m2": 16,
    "load_w": 400,
    "battery_kwh": 20,
    "panel_mode": "horizontal",
    "min_soc_pct": 35,
    "min_local_earth_hours": 6,
    "max_local_earth_gap_hours": 24,
}


def _pdf_has_emblem(data: bytes) -> bool:
    pdf = PdfReader(BytesIO(data))
    return bool(pdf.pages and list(pdf.pages[0].images))


def test_current_public_emblem_is_present_in_source_tree():
    assert LOGO_FILE.is_file()
    assert LOGO_FILE.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "polaris-mission-patch-v2.png" in Path("public/project-home.html").read_text()


def test_simulation_pdf_embeds_new_logo_not_old_vector_mark():
    response = client.post("/api/mission-report.pdf", json=PARAMS)
    assert response.status_code == 200, response.text
    assert _pdf_has_emblem(response.content)
    tex = client.post("/api/mission-report.tex", json=PARAMS)
    assert tex.status_code == 200
    assert r"\includegraphics" in tex.text
    assert "polaris-mission-patch-v2.png" in tex.text


def test_brief_and_dossier_pdf_embed_new_logo():
    for kind in ("brief", "dossier"):
        response = client.post(f"/api/mission-decision/{kind}.pdf", json=PARAMS)
        assert response.status_code == 200, response.text
        assert _pdf_has_emblem(response.content)
        tex = client.post(f"/api/mission-decision/{kind}.tex", json=PARAMS)
        assert tex.status_code == 200
        assert "polaris-mission-patch-v2.png" in tex.text


def test_public_home_team_and_challenge_are_scientifically_qualified():
    home = Path("public/project-home.html").read_text()
    assert "ABOUT THE TEAM" in home and "ABOUT THE CHALLENGE" in home
    assert "not a verified direct-to-Earth radio communication window" in home
    assert "not a NASA-endorsed mission-planning system" in home
