"""
Old entry point, kept so existing code still works. The real logic is in
clarity_reasoner.py.
"""
from decision_engine.clarity_reasoner import reason


def detect_gap_types(text: str) -> list[str]:
    """Which load-bearing gaps the prompt is missing, most important first."""
    return [g["type"] for g in reason(text)["gaps"]]
