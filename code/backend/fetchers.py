"""
Data retrieval for WA, OR, and ID (FR-02). Based on Abby's scripts in code/API/,
but these RETURN the data instead of printing it so the normalizer can use it.

- If a state's API key is in .env  -> call the real API.
- If no key is set                 -> load sample data from sample_data/ (for demos/testing).
- If the real API call fails       -> raise, so the app can skip that state without
                                      breaking the others (US-03 edge case).
"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SAMPLES = Path(__file__).resolve().parent / "sample_data"
TIMEOUT = 15  # seconds


def _sample(name):
    with open(SAMPLES / name) as f:
        return json.load(f)


def fetch_wa():
    key = os.getenv("WA_API_KEY")
    if not key:
        return _sample("wa_sample.json"), "sample"
    url = "https://wsdot.wa.gov/Traffic/api/WeatherInformation/WeatherInformationREST.svc/GetCurrentWeatherInformationAsJson"
    r = requests.get(url, params={"AccessCode": key}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json(), "live"


def fetch_or():
    key = os.getenv("OR_API_KEY")
    if not key:
        return _sample("or_sample.json"), "sample"
    url = "https://api.odot.state.or.us/tripcheck/RW/Reports"
    r = requests.get(url, params={"key": key}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json(), "live"


def fetch_id():
    key = os.getenv("ID_API_KEY")
    if not key:
        return _sample("id_sample.json"), "sample"
    url = "https://511.idaho.gov/api/v3/get/winterroads"
    r = requests.get(url, params={"key": key}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json(), "live"


if __name__ == "__main__":
    # Run `python fetchers.py` with real keys to save one real response per state,
    # so you can check the field names the normalizers expect.
    for name, fn in (("wa", fetch_wa), ("or", fetch_or), ("id", fetch_id)):
        try:
            data, mode = fn()
            out = SAMPLES / f"{name}_real_response.json"
            if mode == "live":
                with open(out, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"{name.upper()}: saved live response to {out.name}")
            else:
                print(f"{name.upper()}: no API key set, using sample data")
        except Exception as e:
            print(f"{name.upper()}: FAILED - {e}")
