"""
siem_connector.py
HTTP-based Elasticsearch helper that:
 - connects to https://localhost:9200 with basic auth and skips TLS verification
 - detects server major version and sets Accept header compatible-with=<major>
 - creates index if missing, inserts documents and performs searches
This avoids client-added incompatible Accept headers and ensures valid JSON bodies.
"""
from typing import Dict, Any, Optional
import json
import base64
import urllib3
from datetime import datetime, timezone

# Configuration - update if needed
ES_URL = "https://localhost:9200"
ES_USER = "elastic"
ES_PASS = "Nava@2004"
FALLBACK_MAJOR = 8  # change to 7 if your server is ES7.x

# Disable TLS cert warnings because verify_certs=False is required
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_http = urllib3.PoolManager(cert_reqs="CERT_NONE")


def _basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def _detect_server_major(timeout: int = 3) -> int:
    """Probe ES root to detect major version (7 or 8)."""
    auth = {"Authorization": _basic_auth_header(ES_USER, ES_PASS)}
    try:
        r = _http.request("GET", ES_URL.rstrip("/"), headers=auth, timeout=timeout)
        if r.status == 200:
            data = json.loads(r.data.decode("utf-8", errors="ignore") or "{}")
            ver = data.get("version", {}).get("number", "")
            if ver:
                major = int(str(ver).split(".")[0])
                if major in (7, 8):
                    return major
    except Exception:
        pass
    return FALLBACK_MAJOR


_ES_MAJOR = _detect_server_major()
_DEFAULT_HEADERS = {
    "Authorization": _basic_auth_header(ES_USER, ES_PASS),
    "Accept": f"application/vnd.elasticsearch+json; compatible-with={_ES_MAJOR}",
    "Content-Type": "application/json",
}


def ensure_index(index: str) -> None:
    """Create index with a basic mapping if it does not exist."""
    url = ES_URL.rstrip("/") + f"/{index}"
    r = _http.request("HEAD", url, headers=_DEFAULT_HEADERS, timeout=10)
    if r.status == 200:
        return
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "user": {"type": "keyword"},
                "event": {"type": "text"},
                "message": {"type": "text"},
                "source": {"properties": {"ip": {"type": "keyword"}}}
            }
        }
    }
    r2 = _http.request(
        "PUT",
        url,
        body=json.dumps(mapping).encode("utf-8"),
        headers=_DEFAULT_HEADERS,
        timeout=10
    )
    if r2.status not in (200, 201):
        body = r2.data.decode("utf-8", errors="ignore")
        raise RuntimeError(f"Failed to create index {index}: HTTP {r2.status}: {body}")


def insert_log(index: str, user: str, event: str, at_timestamp: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Insert a single document into the index. Returns parsed response dict."""
    ensure_index(index)
    if at_timestamp is None:
        at_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    doc: Dict[str, Any] = {"user": user, "event": event, "@timestamp": at_timestamp}
    if extra:
        doc.update(extra)
    url = ES_URL.rstrip("/") + f"/{index}/_doc"
    r = _http.request(
        "POST",
        url,
        body=json.dumps(doc).encode("utf-8"),
        headers=_DEFAULT_HEADERS,
        timeout=10
    )
    resp_body = r.data.decode("utf-8", errors="ignore")
    if r.status >= 400:
        raise RuntimeError(f"Failed to insert doc: HTTP {r.status}: {resp_body}")
    try:
        return json.loads(resp_body or "{}")
    except Exception:
        return {"raw": resp_body}


def search_logs(index: str, query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute _search against index using the provided query dict.
    Returns parsed JSON dict on success, or {'error': str, 'hits': {'hits': []}} on failure.
    """
    try:
        url = ES_URL.rstrip("/") + f"/{index}/_search"
        body = json.dumps(query or {"query": {"match_all": {}}})
        r = _http.request(
            "POST",
            url,
            body=body.encode("utf-8"),
            headers=_DEFAULT_HEADERS,
            timeout=30
        )
        text = r.data.decode("utf-8", errors="ignore")
        if r.status >= 400:
            return {"error": f"HTTP {r.status}: {text}", "hits": {"hits": []}}
        return json.loads(text or "{}")
    except Exception as e:
        return {"error": str(e), "hits": {"hits": []}}


if __name__ == "__main__":
    # Quick diagnostic: insert a sample and search for it
    IDX = "ps01_logs"
    try:
        print("Detected ES major:", _ES_MAJOR)
        print("Ensuring index exists...")
        ensure_index(IDX)
        print("Inserting sample log...")
        ts = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        ins = insert_log(index=IDX, user="admin", event="failed login", at_timestamp=ts, extra={"message": "Failed login test"})
        print("Insert response:", ins)
        print("Searching for admin failed login in last 24h...")
        q = {
            "query": {
                "bool": {
                    "must": [
                        {"match_phrase": {"event": "failed login"}},
                        {"term": {"user": {"value": "admin"}}}
                    ],
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-24h"}}}
                    ]
                }
            },
            "size": 10,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        res = search_logs(index=IDX, query=q)
        print("Search response keys:", list(res.keys()) if isinstance(res, dict) else type(res))
        hits = res.get("hits", {}).get("hits", []) if isinstance(res, dict) else []
        print("Found hits:", len(hits))
        for h in hits:
            print(" -", h.get("_id"), h.get("_source"))
    except Exception as e:
        print("ERROR:", e)