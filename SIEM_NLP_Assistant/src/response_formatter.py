"""
response_formatter.py
Format hits and aggregations into human-friendly structures for CLI/Web.
"""

from typing import Dict, Any, List


def format_hits(es_resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    hits = []
    if not isinstance(es_resp, dict):
        return hits
    for h in es_resp.get("hits", {}).get("hits", []):
        src = h.get("_source", {}) or {}
        entry = {
            "_id": h.get("_id"),
            "timestamp": src.get("@timestamp"),
            "user": src.get("user"),
            "event": src.get("event"),
            "message": src.get("message"),
        }
        hits.append(entry)
    return hits


def format_aggs(es_resp: Dict[str, Any]) -> Dict[str, Any]:
    aggs = es_resp.get("aggregations") or es_resp.get("aggs") or {}
    out = {}
    for k, v in aggs.items():
        # handle terms buckets
        if isinstance(v, dict) and "buckets" in v:
            out[k] = [{"key": b.get("key"), "doc_count": b.get("doc_count")} for b in v.get("buckets", [])]
        else:
            out[k] = v
    return out