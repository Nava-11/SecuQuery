"""
query_generator.py
Build Elasticsearch DSL queries (filters, must) and generate aggregations for
terms/date_histogram use-cases derived from parsed entities.
"""

from typing import Dict, Any, Optional


def build_base_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build bool query from parsed result: event, users, ips, time.
    Returns ES body dict with size/sort defaults.
    """
    must = []
    filters = []

    # event -> prefer match_phrase on event or message
    if parsed.get("event"):
        # map semantic event names to match text
        if parsed["event"] == "failed_login":
            must.append({"match_phrase": {"event": "failed login"}})
        else:
            must.append({"match_phrase": {"event": parsed["event"]}})

    # users -> try keyword term on user field (exact) and fallback to message match
    for u in parsed.get("users", []) or []:
        filters.append({"term": {"user.keyword": {"value": u}}})

    # ips
    for ip in parsed.get("ips", []) or []:
        filters.append({"term": {"source.ip.keyword": {"value": ip}}})

    # time
    if parsed.get("time") and parsed["time"].get("es_range"):
        filters.append({"range": {"@timestamp": parsed["time"]["es_range"]}})
    else:
        # default last 24h
        filters.append({"range": {"@timestamp": {"gte": "now-24h"}}})

    # combine
    boolq = {}
    if must:
        boolq["must"] = must
    if filters:
        boolq["filter"] = filters

    body = {"query": {"bool": boolq}, "size": 100, "sort": [{"@timestamp": {"order": "desc"}}]}
    return body


def build_aggregation(
    parsed: Dict[str, Any],
    agg_type: str,
    field: Optional[str] = None,
    size: int = 10,
    interval: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build aggregations:
      - agg_type: 'terms' | 'date_histogram' | 'top_users' | 'count_per_ip'
      - field: optional ES field if known
    Returns ES body with aggs.
    """
    base = build_base_query(parsed)

    if agg_type == "count_per_ip" or (agg_type == "terms" and (field is None or "ip" in field.lower())):
        # terms aggregation on source.ip.keyword or ip fields
        ip_field = field or "source.ip.keyword"
        base["size"] = 0
        base["aggs"] = {"by_ip": {"terms": {"field": ip_field, "size": size}}}
        return base

    if agg_type == "top_users" or (agg_type == "terms" and (field is None or "user" in field.lower())):
        user_field = field or "user.keyword"
        base["size"] = 0
        base["aggs"] = {"by_user": {"terms": {"field": user_field, "size": size}}}
        return base

    if agg_type == "date_histogram" or (agg_type == "hist" and interval):
        base["size"] = 0
        base["aggs"] = {"timeline": {"date_histogram": {"field": "@timestamp", "fixed_interval": interval}}}
        return base

    # fallback: user-provided agg body
    return base