"""Reproducible competition evidence regression checks."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def test_evidence_export_is_complete_and_provenance_filled():
    file=ROOT/'data/analysis/replanning_matrix_v0.4.csv'
    with file.open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==24
    assert {x['scenario'] for x in rows}=={'original','delayed','alternative_site_after_delay'}
    assert len({x['NASA_data_sha256'] for x in rows})==1
    assert len(rows[0]['NASA_data_sha256'])==64

def test_report_scenario_count():
    file=ROOT/'data/analysis/replanning_evidence_v0.4.json'
    records=json.loads(file.read_text())
    assert len(records)==8
    assert all(r['recommendation'] is None for r in records)
    assert all(len(r['delayed_site_energy_sensitivity'])==4 for r in records)
