"""
main.py
CLI demo: accepts natural queries, builds DSL, optionally runs aggregations,
supports follow-up context inheritance.
"""

from nlp_parser import parse_query
from query_generator import build_base_query, build_aggregation
from siem_connector import search_logs, insert_log, ensure_index
from response_formatter import format_hits, format_aggs
from context_manager import add_interaction, inherit_context
import json

INDEX = "ps01_logs"


def handle_user_input(text: str):
    parsed = parse_query(text)
    # allow inheritance from previous
    parsed = inherit_context(parsed)
    # if user intent is agg or text includes 'count'/'per' try to detect agg type
    if parsed.get("intent") == "agg" or any(k in text.lower() for k in ("count", "per ", "top ", "group ")):
        # simple mapping heuristics
        if "per ip" in text.lower() or "per source ip" in text.lower() or "count per ip" in text.lower():
            body = build_aggregation(parsed, "count_per_ip", size=10)
        elif "top users" in text.lower() or "top 10 users" in text.lower() or "top user" in text.lower():
            body = build_aggregation(parsed, "top_users", size=10)
        elif "histogram" in text.lower() or "timeline" in text.lower() or "per hour" in text.lower():
            body = build_aggregation(parsed, "date_histogram", interval="1h")
        else:
            # fallback to base query (no aggs)
            body = build_base_query(parsed)
    else:
        body = build_base_query(parsed)

    # run search
    resp = search_logs(INDEX, body)
    hits = format_hits(resp)
    aggs = format_aggs(resp)
    add_interaction(text, parsed, resp)
    return {"parsed": parsed, "dsl": body, "hits": hits, "aggs": aggs}


if __name__ == "__main__":
    print("SIEM NLP Assistant CLI. Type 'exit' to quit.")
    # ensure index exists
    ensure_index(INDEX)
    while True:
        txt = input("\nQuery> ").strip()
        if txt.lower() in ("exit", "quit"):
            break
        # convenience: example insert command
        if txt.startswith("!insert "):
            # format: !insert user=admin event='failed login'
            kvs = txt[len("!insert "):]
            doc = {}
            for pair in kvs.split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    v = v.strip("'\"")
                    doc[k] = v
            if "@timestamp" not in doc:
                from datetime import datetime, timezone

                doc["@timestamp"] = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            insert_log(INDEX, doc)
            print("Inserted:", doc)
            continue

        out = handle_user_input(txt)
        print("\nParsed:")
        print(json.dumps(out["parsed"], indent=2))
        print("\nDSL:")
        print(json.dumps(out["dsl"], indent=2))
        print("\nHits (first 10):")
        for h in out["hits"][:10]:
            print(h)
        if out["aggs"]:
            print("\nAggregations:")
            print(json.dumps(out["aggs"], indent=2))