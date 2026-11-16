"""Single source of truth for the public POLARIS mission insignia.

Used by all ReportLab PDF exporters and by optional XeLaTeX builds.
No API credentials, external downloads, or generated images are involved.
"""
from __future__ import annotations
from pathlib import Path

LOGO_FILE = Path(__file__).resolve().parents[1] / "public" / "polaris-mission-patch-v2.png"
LOGO_NAME = LOGO_FILE.name


def draw_polaris_pdf_logo(canvas, x: float, y: float, size: float) -> None:
    """Render the exact logo used on the public project home page."""
    if not LOGO_FILE.is_file():
        raise FileNotFoundError(f"POLARIS official project emblem not packaged: {LOGO_FILE}")
    canvas.drawImage(str(LOGO_FILE), x, y, width=size, height=size,
                     preserveAspectRatio=True, anchor='c', mask='auto')
