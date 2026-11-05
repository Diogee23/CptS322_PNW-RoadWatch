"""
Data retrieval for WA, OR, and ID (FR-02). Uses the same endpoints as Abby's scripts
in code/API/ (PR #24), but these RETURN the data instead of printing it so the
normalizer can use it:
  WA: WSDOT Highway Alerts       (incidents, closures, collisions, weather alerts)
  OR: ODOT TripCheck Incidents   (WazeSpec format)
  ID: Idaho 511 Winter Roads     (road condition segments)

- If a state's API key is in .env  -> call the real API ("live" mode).
- If no key is set                 -> load sample data from sample_data/ ("sample" mode).
- If USE_SAMPLE_DATA=1 in .env     -> always use sample data, even with keys (offline demos).
- If the real API call fails       -> raise FetchError, so the app can skip that state
                                      without breaking the others (US-03 edge case).

We never fall back to sample data when a key IS set and the call fails, because
showing made-up road conditions as if they were real would be worse than showing nothing.

Security (NFR-08): the API keys go in the query string, and `requests` puts the full
URL (key included) into its error messages. FetchError messages are written by us
and never include the URL, so a key can't leak into logs or the /api/status response.
"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SAMPLES = Path(__file__).resolve().parent / "sample_data"
TIMEOUT = 15  # seconds

WA_URL = "https://www.wsdot.wa.gov/Traffic/api/HighwayAlerts/HighwayAlertsREST.svc/GetAlertsAsJson"
OR_URL = "https://api.odot.state.or.us/tripcheck/Incidents/WazeSpec"
ID_URL = "https://511.idaho.gov/api/v3/get/winterroads"


class FetchError(Exception):
    """A state's data couldn't be retrieved. The message is safe to show (no keys/URLs)."""


def _sample(name):
    with open(SAMPLES / name) as f:
        return json.load(f)


def _force_sample():
    return os.getenv("USE_SAMPLE_DATA", "").strip().lower() in ("1", "true", "yes")


def _get_json(agency, url, params):
    """GET a DOT endpoint and return parsed JSON, turning every failure into a clean FetchError."""
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.Timeout:
        raise FetchError(f"{agency} API timed out after {TIMEOUT}s") from None
    except requests.ConnectionError:
        raise FetchError(f"Could not connect to the {agency} API") from None
    except requests.RequestException as e:
        raise FetchError(f"{agency} API request failed ({type(e).__name__})") from None

    if r.status_code in (401, 403):
        raise FetchError(f"{agency} API rejected the key (HTTP {r.status_code}), check the key in .env")
    if r.status_code == 429:
        raise FetchError(f"{agency} API rate limit hit (HTTP 429)")
    if r.status_code != 200:
        raise FetchError(f"{agency} API returned HTTP {r.status_code}")

    try:
        return r.json()
    except ValueError:
        raise FetchError(f"{agency} API returned something that isn't JSON") from None


def _fetch(agency, env_var, sample_file, url, key_param):
    key = (os.getenv(env_var) or "").strip()
    if not key or _force_sample():
        return _sample(sample_file), "sample"
    return _get_json(agency, url, {key_param: key}), "live"


def fetch_wa():
    return _fetch("WSDOT", "WA_API_KEY", "wa_sample.json", WA_URL, "AccessCode")


def fetch_or():
    return _fetch("ODOT", "OR_API_KEY", "or_sample.json", OR_URL, "key")


def fetch_id():
    return _fetch("Idaho 511", "ID_API_KEY", "id_sample.json", ID_URL, "key")


if __name__ == "__main__":
    # Run `python fetchers.py` with real keys to check each key works and save one real
    # response per state, so you can compare field names against what normalize.py expects.
    for name, fn in (("wa", fetch_wa), ("or", fetch_or), ("id", fetch_id)):
        try:
            data, mode = fn()
            if mode == "live":
                out = SAMPLES / f"{name}_real_response.json"
                with open(out, "w") as f:
                    json.dump(data, f, indent=2)
                size = len(data) if isinstance(data, list) else len(data.get("incident", data.get("incidents", data)))
                print(f"{name.upper()}: OK, key works. {size} records saved to {out.name}")
            else:
                print(f"{name.upper()}: no API key set, using sample data")
        except FetchError as e:
            print(f"{name.upper()}: FAILED - {e}")
