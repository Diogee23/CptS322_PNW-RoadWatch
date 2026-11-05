"""Offline test with fake DOT data. Run: python test_flow.py"""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_alerts.db"
if os.path.exists("test_alerts.db"):
    os.remove("test_alerts.db")

from fastapi.testclient import TestClient

import refresh
from db import init_db
import main


def fake(ext_id, sev="Low", src="X"):
    return {
        "ExternalId": ext_id,
        "EventCategory": "Test",
        "HeadlineDescription": f"alert {ext_id}",
        "Severity": sev,
        "Coordinates": {"Latitude": 46.7, "Longitude": -117.1},
        "LastUpdatedTime": "2026-11-04 09:00:00 -0800",
        "Source": src,
    }


state = {
    "WA DOT": [fake("1", "Highest"), fake("2", "Medium"), {"bad": "record"}],
    "OR DOT": [fake("a", "High")],
    "ID DOT": [fake("z", "Unknown")],
}

# Replace fetch/process with fakes: fetch returns the list, process is identity
# except the deliberately bad record, which raises.
def make_process(item):
    if "bad" in item:
        raise KeyError("bad")
    return dict(item)

for name in state:
    refresh.SOURCES[name] = ((lambda n=name: state[n]), make_process)

init_db()
client = TestClient(main.app)

refresh.refresh_all()
alerts = client.get("/alerts").json()
assert len(alerts) == 4, alerts
sev = {a["external_id"]: a["severity"] for a in alerts}
assert sev["1"] == "High" and sev["2"] == "Medium", sev  # WA priority mapped
assert refresh.LAST_RUN["WA DOT"]["skipped"] == 1
print("1. insert + severity mapping + bad-record skip: OK")

# update + disappear
state["WA DOT"] = [fake("1", "Low")]
refresh.refresh_all()
alerts = client.get("/alerts").json()
ids = sorted(a["external_id"] for a in alerts if a["source"] == "WA DOT")
assert ids == ["1"], ids
assert [a for a in alerts if a["external_id"] == "1"][0]["severity"] == "Low"
print("2. update + deactivate vanished alert: OK")

# empty fetch must not wipe data
state["OR DOT"] = []
refresh.refresh_all()
alerts = client.get("/alerts").json()
assert any(a["source"] == "OR DOT" for a in alerts)
assert "kept previous" in refresh.LAST_RUN["OR DOT"]["status"]
print("3. empty fetch keeps old data: OK")

# fetch exception in one state doesn't affect others
def boom():
    raise RuntimeError("api down")
refresh.SOURCES["ID DOT"] = (boom, make_process)
refresh.refresh_all()
assert "fetch error" in refresh.LAST_RUN["ID DOT"]["status"]
assert refresh.LAST_RUN["WA DOT"]["status"] == "ok"
print("4. one state failing is isolated: OK")

# API key protection + health
main.API_TOKEN = "secret"
assert client.get("/alerts").status_code == 401
assert client.get("/alerts", headers={"X-API-Key": "secret"}).status_code == 200
assert client.get("/health").status_code == 200
print("5. API key + /health: OK")

print("sample:", client.get("/alerts", headers={"X-API-Key": "secret"}).json()[0])
os.remove("test_alerts.db")
