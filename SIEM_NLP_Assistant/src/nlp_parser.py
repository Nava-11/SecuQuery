"""
nlp_parser.py
Entity-based parser: spaCy preferred; regex fallback.
Extracts: usernames, IP addresses, event types (failed login, auth error), time ranges.
Returns structured dict consumed by query_generator.
"""

from typing import Dict, Any, Optional
import re

# Try to import spaCy model; if not present, instruct user to download.
try:
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    # Lazy fallback: parse with simple heuristics if spaCy/model not available.
    _NLP = None

IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b")
USER_RE = re.compile(r"\b(?:user|account|by user|by)\s+([-\w.@]+)\b", re.I)
TIME_RE = re.compile(r"\b(?:last|past)\s+(\d+)\s*(hour|hours|day|days|minute|minutes)\b", re.I)

EVENT_KEYWORDS = {
    "failed_login": ["failed login", "failed authentication", "authentication failure", "invalid credentials", "login failed"],
    "success_login": ["successful login", "login success", "authenticated"],
    "ssh_bruteforce": ["brute force", "multiple failed", "failed attempts"],
}


def _detect_event(text: str) -> Optional[str]:
    t = text.lower()
    for evt, kwlist in EVENT_KEYWORDS.items():
        for kw in kwlist:
            if kw in t:
                return evt
    return None


def parse_time_range(text: str) -> Optional[Dict[str, str]]:
    """
    Returns ES range dict like {"gte": "now-24h"} or None.
    """
    m = TIME_RE.search(text)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2).lower()
    if "hour" in unit:
        return {"gte": f"now-{num}h"}
    if "day" in unit:
        return {"gte": f"now-{num}d"}
    if "minute" in unit:
        return {"gte": f"now-{num}m"}
    return None


def parse_query(text: str) -> Dict[str, Any]:
    """
    Returns dict:
      {
        "text": original,
        "users": [..],
        "ips": [..],
        "event": token (like 'failed_login') or None,
        "time": {"es_range": {...}} or None,
        "intent": "search"|"agg" etc
      }
    """
    text = (text or "").strip()
    parsed: Dict[str, Any] = {"text": text, "users": [], "ips": [], "event": None, "time": None, "intent": "search"}

    # Use spaCy if available for tokenization and NER
    if _NLP:
        doc = _NLP(text)
        # usernames: PERSON/ORG tokens or heuristic
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "PRODUCT"):
                parsed["users"].append(ent.text)
        # simple token search for IPs
        for tok in doc:
            if IP_RE.match(tok.text):
                parsed["ips"].append(tok.text)
    else:
        # fallback regex heuristics
        for m in USER_RE.finditer(text):
            parsed["users"].append(m.group(1))
        for m in IP_RE.finditer(text):
            parsed["ips"].append(m.group(0))

    # event detection
    evt = _detect_event(text)
    if evt:
        parsed["event"] = evt

    # time range
    tr = parse_time_range(text)
    if tr:
        parsed["time"] = {"es_range": tr}

    # detect aggregation intent (simple heuristics)
    if re.search(r"\b(count|per|group|top|aggregate|agg|histogram)\b", text, re.I):
        parsed["intent"] = "agg"

    # normalize unique
    parsed["users"] = list(dict.fromkeys(parsed["users"]))
    parsed["ips"] = list(dict.fromkeys(parsed["ips"]))
    return parsed