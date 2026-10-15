# PNW RoadWatch Backend

Pulls road and weather data from the WA, OR, and ID DOT APIs and converts all three into **one common alert format** (FR-02, FR-03, US-03), served at `GET /api/alerts`.

## Run it

```bash
cd code/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5001/api/alerts

## Live data vs sample data

Copy `.env.example` to `.env` and fill in the API keys (same ones Abby's scripts in `code/API/` use).
Any state without a key falls back to `sample_data/`, so the app always runs.
`.env` is git-ignored, so keys never get committed (NFR-08).

To check real field names, run `python fetchers.py` with keys set. It saves one real response per state into `sample_data/`.

## Files

| File | What it does |
|---|---|
| `fetchers.py` | Gets raw data from each state (live API or sample) |
| `normalize.py` | Converts each state's format into the common schema |
| `app.py` | Flask server with the `/api/alerts` endpoint |

## Common alert schema

`id`, `state`, `source`, `type`, `severity` (low/medium/high), `title`, `description`, `lat`, `lng`, `updated` (ISO 8601 UTC)

## Demo URLs

- `/api/alerts`: all three states combined
- `/api/alerts?state=ID`: one state only
- `/api/alerts?simulate_fail=OR`: Oregon "down", WA and ID still load (US-03 edge case)
