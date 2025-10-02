"""
web_app.py
Minimal Flask UI: input box posts to /search, shows parsed params, DSL, hits and aggregations.
Install: pip install flask
Run: python web_app.py
"""
from flask import Flask, request, render_template_string, jsonify
from main import handle_user_input

app = Flask(__name__)

HTML = """
<!doctype html>
<title>SIEM NLP Assistant</title>
<h2>SIEM NLP Assistant</h2>
<form id="qform" method="post" action="/search">
  <input name="q" style="width:60%" placeholder="Type natural language query" />
  <button type="submit">Search</button>
</form>
<pre id="out">{{out}}</pre>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML, out="")

@app.route("/search", methods=["POST"])
def search():
    q = request.form.get("q", "")
    res = handle_user_input(q)
    return render_template_string(HTML, out=jsonify(res).get_data(as_text=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)