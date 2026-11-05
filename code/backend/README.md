# Backend

Pulls road alerts from the WA, OR, and ID DOT APIs, converts them into one alert format, and serves them to the map at `/api/alerts`.

| State | API | What we use from it |
|---|---|---|
| WA | WSDOT Highway Alerts | Incidents, closures, collisions, weather alerts, with WSDOT's priority |
| OR | ODOT TripCheck Incidents (WazeSpec) | Incidents with type (`ROAD_CLOSED`, `ACCIDENT`, `HAZARD`, ...) and description |
| ID | Idaho 511 Winter Roads | Road segments with their condition (Dry, Wet, Icy Patches, Closed, ...) |

The endpoints and field names come from Abby's scripts in `code/API/` (PR #24).

## Run it

```bash
cd code/backend
pip install -r requirements.txt
cp .env.example .env      # then paste in the API keys (ask Abby)
python app.py
```

Open http://localhost:5001/api/alerts. With no keys in `.env` it uses the files in `sample_data/`, so it works out of the box.

To check the keys work, run `python fetchers.py`. It prints OK or the error for each state and saves one real response per state to `sample_data/` (git-ignored) so we can compare field names.

## Endpoints

| URL | What it returns |
|---|---|
| `/api/alerts` | List of all alerts in the format `Alert.fromJSON()` reads |
| `/api/alerts?state=WA` | One state (or `WA,ID` for several) |
| `/api/alerts?min_severity=high` | Only `high` and `critical` |
| `/api/status` | For each state: live or sample, alert count, last success, error message if it failed |
| `/api/health` | `{"ok": true}` |
| `?simulate_fail=OR` | Works on `/api/alerts` and `/api/status`. Pretends Oregon is down (for the demo) |

One alert looks like this:

```json
{
  "alertID": "WA-512345",
  "location": { "latitude": 47.408, "longitude": -121.40415 },
  "alertType": "Weather",
  "severity": "high",
  "description": "I-90: Chains required on vehicles over 10,000 GVW. Traction tires advised.",
  "lastUpdated": "2026-10-15T16:00:00+00:00",
  "sourceAgency": "WA DOT",
  "state": "WA",
  "title": "I-90"
}
```

Severity is `low`, `moderate`, `high`, or `critical`, the same levels as the pin colors. Alerts come back most severe first. How we decide severity:

- **WA:** WSDOT's own `Priority` (Highest → critical, High → high, Medium → moderate, Low/Lowest → low), bumped up if the text says the road is closed.
- **OR:** `ROAD_CLOSED` is critical, accidents are at least moderate, and "minimal delay" or "minor" is low (Abby's rule). Everything else goes by keywords in the description.
- **ID:** by the road condition. Closed is critical, Icy Patches is high, Wet is moderate, Dry is low.
- Full road closures are critical, but lane or shoulder closures are only moderate.

The rules are in `SEVERITY_RULES` at the top of `normalize.py` if we want to tune them.

## When data is unavailable

- **One state is down:** the other states still come back. The failed state is listed in the `X-RoadWatch-Unavailable` response header and in `/api/status`.
- **A state goes down after working:** we keep serving its last good data for up to 30 minutes (marked `stale` in `/api/status`) so its pins don't disappear.
- **Everything is down and nothing is cached:** `/api/alerts` returns HTTP 503. The map already handles this: it keeps the pins it has and shows the warning banner.
- **Bad records** (no coordinates, junk values) are skipped and logged. They don't break the rest of that state.
- **Bad key, timeout, rate limit, non-JSON response:** each gives its own clear message in `/api/status`. API keys never appear in any error message or response.

Responses are cached for 60 seconds, so every user shares one call per minute to each DOT instead of each user calling all three.

## Tests

From the repo root:

```bash
python -m pytest tests/backend -v
```

These use sample data and fake HTTP responses, so they don't need keys or internet.

## Connecting the map

The backend already sends the format the map reads. Once it's hosted somewhere, change the last lines of `code/map/roadwatch-map.js` to:

```js
new MapView("mapViewContainer", { useMock: false, apiUrl: "https://<backend-host>/api/alerts" });
```
