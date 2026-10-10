"""Re-export platform risk heuristic."""

from ._compat import ensure_core_src_on_path

ensure_core_src_on_path()

from mcp_body.risk_classifier import RISK_KEYWORDS, classify_risk_heuristic  # noqa: E402,F401

__all__ = ["RISK_KEYWORDS", "classify_risk_heuristic"]
