"""The public interface must not advertise privileged administration routes."""
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"

def test_no_privileged_navigation_in_public_pages():
    for name in ("workspace.html", "index.html", "workspace.js"):
        content = (PUBLIC / name).read_text(encoding="utf-8").lower()
        assert "/admin" not in content, f"{name} reveals privileged route"

def test_no_admin_text_in_public_login():
    login = (PUBLIC / "workspace.html").read_text(encoding="utf-8").lower()
    assert "administrator" not in login
    assert "pending" in login
