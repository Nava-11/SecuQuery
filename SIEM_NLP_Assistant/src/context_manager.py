"""
context_manager.py
In-memory session context allowing follow-up queries to inherit time/filters.
"""

from typing import Any, Dict, List

_MAX = 50
_context: List[Dict[str, Any]] = []


def add_interaction(query_text: str, parsed: Dict[str, Any], last_result: Dict[str, Any]) -> None:
    _context.append({"query": query_text, "parsed": parsed, "result": last_result})
    if len(_context) > _MAX:
        del _context[0]


def get_last_parsed() -> Dict[str, Any]:
    if not _context:
        return {}
    return _context[-1].get("parsed", {})


def inherit_context(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    If parsed lacks time but last interaction had time, inherit it.
    Other inheritance rules can be added.
    """
    last = get_last_parsed()
    out = dict(parsed)
    if not parsed.get("time") and last.get("time"):
        out["time"] = last["time"]
    return out