"""
PNW RoadWatch backend: GET /api/alerts returns WA, OR, and ID alerts in one common format.

Run:  python app.py   then open http://localhost:5001/api/alerts

Demo extras:
  /api/alerts?state=WA            only one state
  /api/alerts?simulate_fail=OR    pretend Oregon's API is down (US-03 edge case)
"""

import logging

from flask import Flask, jsonify, request

from fetchers import fetch_id, fetch_or, fetch_wa
from normalize import normalize_id, normalize_or, normalize_wa

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.mimetype = "application/json; charset=utf-8"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("roadwatch")

STATES = {
    "WA": (fetch_wa, normalize_wa),
    "OR": (fetch_or, normalize_or),
    "ID": (fetch_id, normalize_id),
}


def get_all_alerts(only=None, simulate_fail=None):
    alerts, status = [], {}
    for state, (fetch, normalize) in STATES.items():
        if only and state != only:
            continue
        try:
            if state == simulate_fail:
                raise ConnectionError("simulated outage")
            raw, mode = fetch()
            normalized = normalize(raw)
            alerts.extend(normalized)
            status[state] = {"ok": True, "mode": mode, "count": len(normalized)}
        except Exception as e:
            # One state failing must not block the others (US-03, scenario 2)
            log.warning("%s DOT fetch failed: %s", state, e)
            status[state] = {"ok": False, "error": str(e)}
    return alerts, status


@app.route("/api/alerts")
def alerts_endpoint():
    only = (request.args.get("state") or "").upper() or None
    fail = (request.args.get("simulate_fail") or "").upper() or None
    alerts, status = get_all_alerts(only, fail)
    return jsonify({"count": len(alerts), "sources": status, "alerts": alerts})


@app.route("/")
def home():
    return '<p>PNW RoadWatch backend is running. Try <a href="/api/alerts">/api/alerts</a></p>'


if __name__ == "__main__":
    app.run(debug=True, port=5001)
