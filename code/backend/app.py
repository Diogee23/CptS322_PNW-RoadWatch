"""
PNW RoadWatch backend.

Run:  python app.py   then open http://localhost:5001/api/alerts

Endpoints
  GET /api/alerts                 all WA, OR, and ID alerts as a JSON list (the format the map expects)
  GET /api/alerts?state=WA        only one state (WA, OR, or ID; comma-separate for more: WA,ID)
  GET /api/alerts?min_severity=high   only alerts at or above a severity
  GET /api/status                 per-state health: live or sample data, count, last update, errors
  GET /api/health                 simple "is the server up" check

Demo extras (for the sprint video):
  /api/alerts?simulate_fail=OR    pretend Oregon's API is down (US-03 edge case)
  /api/status?simulate_fail=OR    same, but shows what the status page reports

How "data unavailable" is handled
  - One state failing never blocks the others; its alerts are just left out.
  - If a state fails but we fetched it successfully in the last STALE_LIMIT seconds,
    we keep serving that last good copy (marked "stale" in /api/status) instead of
    making its pins vanish.
  - If every requested state fails and there's nothing cached, /api/alerts returns
    HTTP 503. The map treats any non-200 as "fetch failed", keeps the pins it already
    has, and shows its warning banner.
  - A state that works but simply has no alerts right now returns an empty list (200).
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from fetchers import FetchError, fetch_id, fetch_or, fetch_wa
from normalize import SEVERITIES, normalize_id, normalize_or, normalize_wa

load_dotenv()

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

# NFR-02: the map refreshes every 60s. Caching for the same window means all users
# share one call to each DOT per minute instead of each user hitting all three APIs.
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "60"))
STALE_LIMIT = int(os.getenv("STALE_LIMIT_SECONDS", "1800"))  # serve last good data for up to 30 min

# Who's allowed to call the API from a browser. The site is on GitHub Pages and the
# backend runs somewhere else, so without this header the browser blocks the request.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

_cache = {}  # state -> {"alerts", "fetched_at", "mode", "last_error", "last_error_at"}
_lock = threading.Lock()


def _now_iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None


def clear_cache():
    with _lock:
        _cache.clear()


def get_state_alerts(state, simulate_fail=False):
    """
    Return (alerts, status) for one state. Never raises: failures go into status.
    """
    fetch, normalize = STATES[state]
    now = time.time()
    with _lock:
        entry = dict(_cache.get(state, {}))

    fresh = entry.get("fetched_at") and now - entry["fetched_at"] < CACHE_SECONDS
    if fresh and not simulate_fail:
        return entry["alerts"], _status(entry, ok=True, now=now)

    try:
        if simulate_fail:
            raise FetchError("simulated outage (demo)")
        raw, mode = fetch()
        try:
            alerts = normalize(raw)
        except ValueError as e:
            raise FetchError(f"{state} data was in an unexpected format: {e}") from None
        entry = {"alerts": alerts, "fetched_at": now, "mode": mode,
                 "last_error": None, "last_error_at": None}
        with _lock:
            _cache[state] = entry
        return alerts, _status(entry, ok=True, now=now)

    except Exception as e:
        # FetchError messages are safe to show. Anything else is a bug on our side,
        # so log it fully but don't send internals to the client.
        message = str(e) if isinstance(e, FetchError) else "internal error while processing data"
        if isinstance(e, FetchError):
            log.warning("%s fetch failed: %s", state, message)
        else:
            log.exception("%s: unexpected error", state)

        entry["last_error"], entry["last_error_at"] = message, now
        with _lock:
            if state in _cache:
                _cache[state].update(last_error=message, last_error_at=now)

        age = now - entry["fetched_at"] if entry.get("fetched_at") else None
        if age is not None and age <= STALE_LIMIT:
            # Keep showing the last good data rather than making the pins disappear
            return entry["alerts"], _status(entry, ok=False, now=now, stale=True)
        return [], _status(entry, ok=False, now=now)


def _status(entry, ok, now, stale=False):
    s = {
        "ok": ok,
        "mode": entry.get("mode"),  # "live" (real API) or "sample" (no key set)
        "count": len(entry.get("alerts", [])) if (ok or stale) else 0,
        "last_success": _now_iso(entry.get("fetched_at")),
        "stale": stale,
    }
    if not ok:
        s["error"] = entry.get("last_error")
    if stale:
        s["data_age_seconds"] = int(now - entry["fetched_at"])
    return s


def get_all_alerts(only=None, simulate_fail=()):
    """Fetch every requested state (or all). Returns (alerts, {state: status})."""
    alerts, status = [], {}
    for state in STATES:
        if only and state not in only:
            continue
        state_alerts, status[state] = get_state_alerts(state, simulate_fail=state in simulate_fail)
        alerts.extend(state_alerts)
    return alerts, status


def _parse_states(value, param):
    """'wa, id' -> {'WA', 'ID'}. Raises ValueError on an unknown state."""
    if not value:
        return set()
    states = {s.strip().upper() for s in value.split(",") if s.strip()}
    unknown = states - set(STATES)
    if unknown:
        raise ValueError(f"unknown state in '{param}': {', '.join(sorted(unknown))}. Use WA, OR, or ID.")
    return states


def _read_filters():
    only = _parse_states(request.args.get("state"), "state") or None
    fail = _parse_states(request.args.get("simulate_fail"), "simulate_fail")
    min_sev = (request.args.get("min_severity") or "").strip().lower() or None
    if min_sev and min_sev not in SEVERITIES:
        raise ValueError(f"min_severity must be one of: {', '.join(SEVERITIES)}")
    return only, fail, min_sev


@app.route("/api/alerts")
def alerts_endpoint():
    try:
        only, fail, min_sev = _read_filters()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    alerts, status = get_all_alerts(only, fail)

    if not any(s["ok"] or s["stale"] for s in status.values()):
        return jsonify({"error": "Alert data is unavailable right now. Please try again shortly.",
                        "sources": status}), 503

    if min_sev:
        floor = SEVERITIES.index(min_sev)
        alerts = [a for a in alerts if SEVERITIES.index(a["severity"]) >= floor]

    # Most serious first, so the worst alerts are drawn on top
    alerts.sort(key=lambda a: SEVERITIES.index(a["severity"]), reverse=True)

    resp = jsonify(alerts)
    failed = [s for s, st in status.items() if not st["ok"]]
    if failed:
        # Lets the frontend know the list is partial without changing the list format
        resp.headers["X-RoadWatch-Unavailable"] = ",".join(failed)
    return resp


@app.route("/api/status")
def status_endpoint():
    try:
        only, fail, _ = _read_filters()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    alerts, status = get_all_alerts(only, fail)
    return jsonify({
        "ok": all(s["ok"] for s in status.values()),
        "total_alerts": len(alerts),
        "cache_seconds": CACHE_SECONDS,
        "sources": status,
    })


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/")
def home():
    return ('<p>PNW RoadWatch backend is running. Try <a href="/api/alerts">/api/alerts</a> '
            'or <a href="/api/status">/api/status</a></p>')


@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    if "*" in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Expose-Headers"] = "X-RoadWatch-Unavailable"
    return resp


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found. Try /api/alerts or /api/status."}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({"error": "Something went wrong on the server."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5001")))
