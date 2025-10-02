# SIEM_NLP_Assistant

SIEM NLP Assistant lets you type natural language queries (e.g. "Search for failed login attempts by user admin in last 24 hours") and runs equivalent Elasticsearch DSL queries against an index (ps01_logs). It supports CLI and a minimal Flask web UI, NLP parsing (spaCy or fallback heuristics), aggregation generation, and simple session context inheritance.

## Features

- Natural language parsing (spaCy; regex fallback)
- Generates Elasticsearch DSL (search + aggregations)
- Inserts and searches documents in `ps01_logs`
- CLI and optional Flask web interface
- Session context for follow-up queries
- Works with HTTPS ES endpoints; TLS verification may be disabled (verify_certs=False)

## Quick start

1. Clone the repo and change into the project:

   ```
   cd c:\Users\navan\Downloads\sih\SIEM_NLP_Assistant
   ```

2. Install Python dependencies:

   ```
   python -m pip install -r requirements.txt
   ```

3. (Optional but recommended) Install spaCy model:

   ```
   python -m spacy download en_core_web_sm
   ```

4. Configure Elasticsearch connection (if needed):

   - Default is https://localhost:9200 with username `elastic` and password `Nava@2004`.
   - To change, edit `src/siem_connector.py` constants: `ES_URL`, `ES_USER`, `ES_PASS`, and `FALLBACK_MAJOR`.

5. Run the CLI:

   ```
   python src\main.py
   ```

   Example queries:

   - Search for failed login attempts by user admin in last 24 hours
   - Count failed logins per source IP in last 24 hours
   - !insert user=admin event='failed login' message='...' (convenience insert)

6. Run the web UI (Flask):
   ```
   python src\web_app.py
   ```
   Open http://localhost:5000

## Example (CLI)

- Insert a document:
  ```
  !insert user=admin event='failed login' message='Failed login from 10.0.0.5'
  ```
- Query:
  ```
  Search for failed login attempts by user admin in last 24 hours
  ```

## Troubleshooting

- Media-type / compatible-with error:

  - If Elasticsearch complains about Accept headers (e.g. `compatible-with=9`), set `FALLBACK_MAJOR` or detected server major in `src/siem_connector.py` to match your ES server major (7 or 8).
  - Alternatively install the client matching your ES server: `pip install "elasticsearch==8.*"` for ES 8.x or `pip install "elasticsearch==7.*"` for ES 7.x.

- TLS verification:

  - The code disables TLS verification (per project spec). For production, enable cert verification and provide CA bundle.

- spaCy model:
  - If parsing is poor, ensure `en_core_web_sm` is installed.

## Files of interest

- src/main.py — CLI entry point
- src/web_app.py — Flask web UI
- src/nlp_parser.py — NLP parsing (spaCy + regex fallback)
- src/query_generator.py — Build ES query / aggregations
- src/siem_connector.py — ES connection, ensure index, insert, search
- src/response_formatter.py — Format hits and aggregations
- src/context_manager.py — In-memory session context

## Notes

- This project is a prototype. Review and harden authentication, TLS, input handling, and mapping before production use.
