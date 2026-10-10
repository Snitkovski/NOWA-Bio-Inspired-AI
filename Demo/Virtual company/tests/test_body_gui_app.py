"""Smoke tests for the Body Layer GUI module (no window)."""

from nowa_body.gui_app import BodyLabApp, DEMO_ROOT, main
from nowa_body.lab_session import BodyLabSession


def test_gui_module_exports_app_and_demo_root():
    assert BodyLabApp is not None
    assert callable(main)
    assert DEMO_ROOT.name == "Virtual company"
    assert (DEMO_ROOT / "src" / "nowa_body" / "gui_app.py").is_file()


def test_session_default_is_ready_for_gui_first_tick():
    session = BodyLabSession()
    result = session.tick_once()
    assert result["proposed"] is not None
    assert result["approval_status"] in {"pending", "approved"}
    if result["approval_status"] == "pending":
        assert session.pending_rows()
    else:
        assert result.get("executed") is True
