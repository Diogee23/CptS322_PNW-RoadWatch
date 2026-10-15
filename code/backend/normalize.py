"""
Normalization layer for PNW RoadWatch (FR-03, US-03).

Each state DOT returns data in its own format. These functions convert
each format into ONE common alert schema so the map can treat them all the same:

    {
        "id":          "WA-1234",         # state prefix + the source's own id
        "state":       "WA",
        "source":      "WSDOT",           # agency shown on each alert (NFR-07)
        "type":        "weather" | "road_condition",
        "severity":    "low" | "medium" | "high",
        "title":       "Snoqualmie Pass", # short name for the pin
        "description": "Snow, 28°F",      # human-readable details
        "lat":         47.42,
        "lng":         -121.41,
        "updated":     "2026-10-15T09:30:00+00:00"  # ISO 8601, UTC
    }

NOTE: field names for Oregon and Idaho are based on what the APIs are expected
to return. Run fetchers.py with real keys and compare against the actual
response; if a field name is different, fix it in `pick(...)` below.
"""

import re
from datetime import datetime, timezone


# ---------- small helpers ----------

def pick(record, *keys, default=None):
    """Return the first key that exists and isn't empty (APIs name things differently)."""
    for key in keys:
        value = record.get(key)
        if value not in (None, "", "null"):
            return value
    return default


def classify_severity(text):
    """Very simple keyword rule: closures are high, winter conditions are medium."""
    text = (text or "").lower()
    if any(w in text for w in ("closed", "closure", "impassable", "blocked")):
        return "high"
    if any(w in text for w in ("snow", "ice", "icy", "chain", "slush", "freezing", "fog", "sleet")):
        return "medium"
    return "low"


def to_iso(value):
    """Convert the different timestamp formats the states use into ISO 8601 UTC."""
    if value in (None, ""):
        return None
    # WSDOT style: "/Date(1760542200000-0700)/"
    if isinstance(value, str) and value.startswith("/Date("):
        millis = int(re.search(r"-?\d+", value).group())
        return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()
    # Unix seconds (Idaho 511 style)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    # Already a date string, try to parse it, otherwise pass it through
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return str(value)


def decode_polyline_first_point(encoded):
    """Idaho gives road segments as Google encoded polylines; take the first point as the pin location."""
    if not encoded:
        return None, None
    coords, index, lat, lng = [], 0, 0, 0
    while index < len(encoded) and len(coords) < 1:
        for which in ("lat", "lng"):
            shift, result = 0, 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if which == "lat":
                lat += delta
            else:
                lng += delta
        coords.append((lat / 1e5, lng / 1e5))
    return coords[0] if coords else (None, None)


# ---------- one normalizer per state ----------

def normalize_wa(raw_list):
    """WSDOT Weather Information: a list of weather station readings."""
    alerts = []
    for r in raw_list:
        temp = pick(r, "TemperatureInFahrenheit")
        sky = pick(r, "SkyCoverage", default="")
        precip = pick(r, "PrecipitationInInches")
        details = [str(sky)] if sky else []
        if temp is not None:
            details.append(f"{temp}°F")
        if precip:
            details.append(f'{precip}" precip')
        description = ", ".join(details) or "Weather station reading"

        # Freezing temps with precipitation count as a winter condition
        severity = classify_severity(sky)
        if temp is not None and precip and float(temp) <= 32:
            severity = "medium"

        alerts.append({
            "id": f"WA-{pick(r, 'StationID', default='?')}",
            "state": "WA",
            "source": "WSDOT",
            "type": "weather",
            "severity": severity,
            "title": pick(r, "StationName", default="WSDOT station"),
            "description": description,
            "lat": pick(r, "Latitude"),
            "lng": pick(r, "Longitude"),
            "updated": to_iso(pick(r, "ReadingTime")),
        })
    return alerts


def normalize_or(raw):
    """ODOT TripCheck road-weather reports (field names: verify against a real response)."""
    reports = raw.get("road-weather-reports", []) if isinstance(raw, dict) else raw
    alerts = []
    for r in reports:
        road = pick(r, "road-condition", "roadCondition", "RoadCondition", default="")
        weather = pick(r, "weather-condition", "weatherCondition", "WeatherCondition", default="")
        description = ", ".join(x for x in (weather, road) if x) or "Road weather report"
        alerts.append({
            "id": f"OR-{pick(r, 'report-id', 'id', 'location-id', default='?')}",
            "state": "OR",
            "source": "ODOT",
            "type": "road_condition",
            "severity": classify_severity(f"{road} {weather}"),
            "title": pick(r, "location-name", "locationName", "station-name", default="ODOT report"),
            "description": description,
            "lat": pick(r, "latitude", "lat", "Latitude"),
            "lng": pick(r, "longitude", "lon", "lng", "Longitude"),
            "updated": to_iso(pick(r, "entry-time", "last-updated", "lastUpdated", "timestamp")),
        })
    return alerts


def normalize_id(raw_list):
    """Idaho 511 winter roads: road segments with condition text and an encoded polyline."""
    alerts = []
    for r in raw_list:
        weather = pick(r, "Weather Conditions", "WeatherConditions", default="")
        road = pick(r, "Primary Condition", "RoadCondition", "Road Condition", default="")
        if not weather:
            continue  # same filter Abby used: skip segments with no weather info
        lat, lng = pick(r, "Latitude"), pick(r, "Longitude")
        if lat is None:
            lat, lng = decode_polyline_first_point(pick(r, "EncodedPolyline"))
        alerts.append({
            "id": f"ID-{pick(r, 'Id', 'ID', default='?')}",
            "state": "ID",
            "source": "ITD (Idaho 511)",
            "type": "road_condition",
            "severity": classify_severity(f"{road} {weather}"),
            "title": pick(r, "RoadwayName", "Roadway", "AreaName", default="Idaho road segment"),
            "description": ", ".join(x for x in (weather, road) if x),
            "lat": lat,
            "lng": lng,
            "updated": to_iso(pick(r, "LastUpdated", "Last Updated")),
        })
    return alerts
