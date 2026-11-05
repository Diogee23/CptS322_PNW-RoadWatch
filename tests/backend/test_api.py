"""
Endpoint tests for the alerts backend. These run against sample data and fake
HTTP responses, so they don't need API keys or internet.

Run from the repo root:  python -m pytest tests/backend -v
"""

import requests

import app as app_module
import fetchers

# Exactly the fields the map's Alert.fromJSON() reads (code/map/models.js)
FRONTEND_FIELDS = {"alertID", "location", "alertType", "severity", "description", "lastUpdated", "sourceAgency"}
MAP_SEVERITIES = {"low", "moderate", "high", "critical"}  # the four pin colors in roadwatch-map.css


class FakeResponse:
    def __init__(self, status_code=200, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


def fake_get(responses):
    """Patch requests.get to answer per-URL. A value can be a FakeResponse or an exception to raise."""
    calls = []

    def _get(url, params=None, timeout=None):
        calls.append((url, params))
        result = responses[url]
        if isinstance(result, Exception):
            raise result
        return result

    _get.calls = calls
    return _get


# ---------- format: what the frontend gets ----------

def test_alerts_returns_list_in_frontend_format(client):
    r = client.get("/api/alerts")
    assert r.status_code == 200
    alerts = r.get_json()
    assert isinstance(alerts, list)  # the map does raw.map(Alert.fromJSON), so it must be a list
    assert len(alerts) > 0
    for a in alerts:
        assert FRONTEND_FIELDS <= a.keys()
        assert a["severity"] in MAP_SEVERITIES
        assert isinstance(a["location"]["latitude"], float)
        assert isinstance(a["location"]["longitude"], float)
        assert a["sourceAgency"] in {"WA DOT", "OR DOT", "ID DOT"}


def test_alerts_include_all_three_states(client):
    states = {a["state"] for a in client.get("/api/alerts").get_json()}
    assert states == {"WA", "OR", "ID"}


def test_alert_ids_are_unique(client):
    ids = [a["alertID"] for a in client.get("/api/alerts").get_json()]
    assert len(ids) == len(set(ids))


def test_most_severe_alerts_come_first(client):
    order = ["low", "moderate", "high", "critical"]
    sev = [order.index(a["severity"]) for a in client.get("/api/alerts").get_json()]
    assert sev == sorted(sev, reverse=True)


def test_cors_header_lets_github_pages_call_the_api(client):
    r = client.get("/api/alerts", headers={"Origin": "https://diogee23.github.io"})
    assert r.headers.get("Access-Control-Allow-Origin") in ("*", "https://diogee23.github.io")


# ---------- filters ----------

def test_filter_by_one_state(client):
    alerts = client.get("/api/alerts?state=wa").get_json()
    assert alerts and all(a["state"] == "WA" for a in alerts)


def test_filter_by_multiple_states(client):
    states = {a["state"] for a in client.get("/api/alerts?state=WA,ID").get_json()}
    assert states == {"WA", "ID"}


def test_unknown_state_is_400(client):
    r = client.get("/api/alerts?state=CA")
    assert r.status_code == 400
    assert "CA" in r.get_json()["error"]


def test_min_severity_filter(client):
    alerts = client.get("/api/alerts?min_severity=high").get_json()
    assert alerts and all(a["severity"] in ("high", "critical") for a in alerts)


def test_bad_min_severity_is_400(client):
    assert client.get("/api/alerts?min_severity=extreme").status_code == 400


# ---------- one state down / data unavailable ----------

def test_one_state_down_still_returns_the_others(client):
    r = client.get("/api/alerts?simulate_fail=OR")
    assert r.status_code == 200
    states = {a["state"] for a in r.get_json()}
    assert "OR" not in states and {"WA", "ID"} <= states
    assert r.headers["X-RoadWatch-Unavailable"] == "OR"


def test_status_reports_which_state_failed(client):
    body = client.get("/api/status?simulate_fail=OR").get_json()
    assert body["ok"] is False
    assert body["sources"]["OR"]["ok"] is False
    assert "simulated" in body["sources"]["OR"]["error"]
    assert body["sources"]["WA"]["ok"] is True


def test_all_states_down_is_503(client):
    r = client.get("/api/alerts?simulate_fail=WA,OR,ID")
    assert r.status_code == 503  # map sees !res.ok, keeps its cached pins, and shows the banner
    assert "unavailable" in r.get_json()["error"].lower()


def test_failed_state_serves_last_good_data(client):
    first = {a["alertID"] for a in client.get("/api/alerts?state=OR").get_json()}
    r = client.get("/api/alerts?state=OR&simulate_fail=OR")
    assert r.status_code == 200
    assert {a["alertID"] for a in r.get_json()} == first
    status = client.get("/api/status?state=OR&simulate_fail=OR").get_json()["sources"]["OR"]
    assert status["stale"] is True and status["ok"] is False


def test_stale_data_expires(client, monkeypatch):
    client.get("/api/alerts?state=OR")
    monkeypatch.setattr(app_module, "STALE_LIMIT", -1)  # pretend the cache is too old
    assert client.get("/api/alerts?state=OR&simulate_fail=OR").status_code == 503


def test_state_with_no_alerts_returns_empty_list(client, monkeypatch):
    monkeypatch.setitem(app_module.STATES, "WA", (lambda: ([], "live"), app_module.normalize_wa))
    r = client.get("/api/alerts?state=WA")
    assert r.status_code == 200
    assert r.get_json() == []


def test_unexpected_response_shape_is_handled(client, monkeypatch):
    monkeypatch.setitem(app_module.STATES, "OR", (lambda: ("<html>oops</html>", "live"), app_module.normalize_or))
    body = client.get("/api/status?state=OR").get_json()
    assert body["sources"]["OR"]["ok"] is False
    assert "unexpected format" in body["sources"]["OR"]["error"]


# ---------- live mode with fake HTTP ----------

def test_live_mode_uses_the_key(client, monkeypatch):
    monkeypatch.setenv("WA_API_KEY", "test-key-123")
    alert = {"AlertID": 1, "Priority": "High", "EventCategory": "Weather",
             "HeadlineDescription": "Chains required", "LastUpdatedTime": "/Date(1792080000000-0700)/",
             "StartRoadwayLocation": {"RoadName": "I-90", "Latitude": 47.0, "Longitude": -121.0}}
    get = fake_get({fetchers.WA_URL: FakeResponse(200, [alert])})
    monkeypatch.setattr(fetchers.requests, "get", get)

    alerts = client.get("/api/alerts?state=WA").get_json()
    assert get.calls[0][1] == {"AccessCode": "test-key-123"}
    assert alerts[0]["alertID"] == "WA-1" and alerts[0]["severity"] == "high"
    assert client.get("/api/status?state=WA").get_json()["sources"]["WA"]["mode"] == "live"


def test_results_are_cached(client, monkeypatch):
    monkeypatch.setenv("WA_API_KEY", "k")
    get = fake_get({fetchers.WA_URL: FakeResponse(200, [])})
    monkeypatch.setattr(fetchers.requests, "get", get)
    client.get("/api/alerts?state=WA")
    client.get("/api/alerts?state=WA")
    assert len(get.calls) == 1  # second request was served from cache


def test_force_sample_mode(client, monkeypatch):
    monkeypatch.setenv("WA_API_KEY", "k")
    monkeypatch.setenv("USE_SAMPLE_DATA", "1")
    monkeypatch.setattr(fetchers.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    assert client.get("/api/alerts?state=WA").status_code == 200


def _status_error(client, monkeypatch, state, env, url, result):
    monkeypatch.setenv(env, "SECRET-KEY-DO-NOT-LEAK")
    monkeypatch.setattr(fetchers.requests, "get", fake_get({url: result}))
    return client.get(f"/api/status?state={state}").get_json()["sources"][state]


def test_timeout_is_reported(client, monkeypatch):
    s = _status_error(client, monkeypatch, "OR", "OR_API_KEY", fetchers.OR_URL, requests.Timeout("slow"))
    assert s["ok"] is False and "timed out" in s["error"]


def test_connection_error_is_reported(client, monkeypatch):
    s = _status_error(client, monkeypatch, "ID", "ID_API_KEY", fetchers.ID_URL, requests.ConnectionError("down"))
    assert "connect" in s["error"].lower()


def test_bad_key_is_reported(client, monkeypatch):
    s = _status_error(client, monkeypatch, "WA", "WA_API_KEY", fetchers.WA_URL, FakeResponse(401))
    assert "key" in s["error"] and "401" in s["error"]


def test_server_error_is_reported(client, monkeypatch):
    s = _status_error(client, monkeypatch, "OR", "OR_API_KEY", fetchers.OR_URL, FakeResponse(500))
    assert "500" in s["error"]


def test_non_json_response_is_reported(client, monkeypatch):
    s = _status_error(client, monkeypatch, "ID", "ID_API_KEY", fetchers.ID_URL, FakeResponse(200, bad_json=True))
    assert "JSON" in s["error"]


def test_api_key_never_leaks_in_errors(client, monkeypatch):
    # requests puts the full URL (with ?key=...) in its exception text; make sure we don't pass that on
    leaky = requests.ConnectionError(f"Max retries exceeded with url: {fetchers.OR_URL}?key=SECRET-KEY-DO-NOT-LEAK")
    monkeypatch.setenv("OR_API_KEY", "SECRET-KEY-DO-NOT-LEAK")
    monkeypatch.setattr(fetchers.requests, "get", fake_get({fetchers.OR_URL: leaky}))
    for path in ("/api/status?state=OR", "/api/alerts?state=OR"):
        assert "SECRET-KEY" not in client.get(path).get_data(as_text=True)


# ---------- misc ----------

def test_health(client):
    assert client.get("/api/health").get_json() == {"ok": True}


def test_unknown_route_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and "error" in r.get_json()
