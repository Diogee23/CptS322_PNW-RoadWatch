"""
Flask backend that aggregates the WA, OR and ID DOT normalizers into one API.

Run:
    pip install flask flask-cors requests python-dotenv polyline
    python app.py

Then expose it with Cloudflare:
    cloudflared tunnel --url http://localhost:5000
"""
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
load_dotenv()  # load .env before reading any settings below

from WA import normalize_wa_data
from OR import normalize_oregon_data
from ID import normalize_idaho_data

app = Flask(__name__)

# Allow the front end (served from a different origin) to call this API.
# Set FRONTEND_ORIGIN in .env, e.g. https://my-frontend.pages.dev
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
CORS(
    app,
    origins=["https://diogee23.github.io"])

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

SOURCES = {
    "WA": normalize_wa_data,
    "OR": normalize_oregon_data,
    "ID": normalize_idaho_data,
}



@app.get("/")
def index():
    return jsonify({"routes": sorted(str(r) for r in app.url_map.iter_rules())})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "states": list(SOURCES)})


@app.get("/api/alerts")
def alerts():
    id_data = normalize_idaho_data()
    or_data = normalize_oregon_data()
    wa_data = normalize_wa_data()
    complete_data = id_data + or_data + wa_data
    return jsonify(complete_data)


@app.errorhandler(404)
def not_found(_e):
    return jsonify({
        "error": "Not found",
        "path": request.path,
        "routes": sorted(str(r) for r in app.url_map.iter_rules()),
    }), 404


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    # Bind to localhost only; Cloudflare Tunnel reaches it from there.
    app.run(host="127.0.0.1", port=port, debug=False)