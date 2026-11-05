"""
Normalization layer for PNW RoadWatch (FR-03, US-03).

Each state DOT returns data in its own format. These functions convert each format
into ONE common alert schema. The field names match the Alert class from our class
diagram (code/map/models.js), so the map can use Alert.fromJSON() on each item as-is:

    {
        "alertID":      "WA-512345",            # state prefix + the source's own id
        "location":     {"latitude": 47.42, "longitude": -121.41},
        "alertType":    "Weather",            # short label, shown as the popup heading
        "severity":     "low" | "moderate" | "high" | "critical",
        "description":  "I-90: Chains required on vehicles over 10,000 GVW",
        "lastUpdated":  "2026-10-15T09:30:00+00:00",   # ISO 8601, UTC (or null)
        "sourceAgency": "WA DOT" | "OR DOT" | "ID DOT", # NFR-07
        "state":        "WA",                 # extras: not used by the map yet, but handy
        "title":        "I-90"                #   for filtering and debugging
    }

Bad records are skipped instead of crashing the whole state: a record with no usable
coordinates can't be drawn as a pin, and the map would throw on it.

Field names come from the real API responses Abby worked with (PR #24, code/API/).
If a state changes its format, run fetchers.py with real keys and update the
`pick(...)` calls below.
"""

import logging
import re
from datetime import datetime, timezone

log = logging.getLogger("roadwatch")

SEVERITIES = ("low", "moderate", "high", "critical")  # same levels the map's pin colors use

# Rough box around WA/OR/ID. Catches swapped lat/lng and (0, 0) junk values.
LAT_RANGE = (40.0, 50.0)
LNG_RANGE = (-126.0, -110.0)

# Checked top to bottom; the first match wins, so the most serious rules go first.
SEVERITY_RULES = [
    # A whole road closed is critical; a lane or shoulder closed is not
    (r"\b(?:road|highway|pass|bridge|interstate|route|freeway)s? (?:is |are |remains? )?closed\b"
     r"|\bclosed (?:in )?both directions\b|\bfull closure\b|\bimpassable\b|^closed$", "critical", "Road Closed"),
    (r"\b(?:lanes?|shoulders?|ramps?|exits?) (?:is |are )?(?:closed|blocked)\b|\blane closures?\b"
     r"|\bblocking (?:the )?(?:\w+ )?lanes?\b", "moderate", "Lane Closure"),
    (r"\bclosed\b|\bclosures?\b|\bblocked\b", "high", "Closure"),
    (r"\bchains?\b|\btraction tires?\b", "high", "Chains Required"),
    (r"\blandslides?\b|\bhazardous materials?\b|\bhazmat\b|\brockslides?\b", "high", "Hazard"),
    (r"\bblack ice\b|\bice\b|\bicy\b|\bfreezing rain\b", "high", "Ice"),
    (r"\bheavy snow\b|\bblowing snow\b|\bblizzard\b", "high", "Heavy Snow"),
    (r"\bsnow\w*\b|\bsleet\b|\bslush\w*\b|\bflurr\w*\b|\bhail\b", "moderate", "Snow"),
    (r"\bfog\w*\b|\bsmoke\b|\blow visibility\b", "moderate", "Low Visibility"),
    (r"\bcollisions?\b|\bcrash\w*\b|\bdisabled vehicle\b|\bdebris\b", "moderate", "Collision"),
    (r"\bwet\b|\bstanding water\b|\bflood\w*\b", "moderate", "Wet Roads"),
]


# ---------- small helpers ----------

def pick(record, *keys, default=None):
    """Return the first key that exists and isn't empty (APIs name things differently)."""
    for key in keys:
        value = record.get(key)
        if value not in (None, "", "null"):
            return value
    return default


def classify(text, default_label="Conditions Report"):
    """Keyword rules -> (severity, short label). Closures are critical, chains/ice high, etc."""
    text = " ".join((text or "").lower().split())
    for pattern, severity, label in SEVERITY_RULES:
        if re.search(pattern, text):
            return severity, label
    return "low", default_label


def raise_severity(current, minimum):
    """Bump a severity up to at least `minimum` (never lowers it)."""
    return max(current, minimum, key=SEVERITIES.index)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def valid_location(lat, lng):
    """Return {"latitude", "longitude"} if the point is a real spot in the PNW, else None."""
    lat, lng = to_float(lat), to_float(lng)
    if lat is None or lng is None:
        return None
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LNG_RANGE[0] <= lng <= LNG_RANGE[1]):
        return None
    return {"latitude": round(lat, 6), "longitude": round(lng, 6)}


def to_iso(value):
    """Convert the different timestamp formats the states use into ISO 8601 UTC (None if unreadable)."""
    if value in (None, ""):
        return None
    try:
        # WSDOT style: "/Date(1760542200000-0700)/"
        if isinstance(value, str) and value.startswith("/Date("):
            millis = int(re.search(r"-?\d+", value).group())
            return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()
        # Unix seconds (Idaho 511 style); some APIs send milliseconds instead
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
        # Already a date string
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError, AttributeError):
        return None  # the map shows a missing time better than a garbage one


def decode_polyline(encoded):
    """Decode a Google encoded polyline (Idaho 511 format) into [(lat, lng), ...]. [] if corrupt."""
    if not encoded or not isinstance(encoded, str):
        return []
    points, index, lat, lng = [], 0, 0, 0
    try:
        while index < len(encoded):
            deltas = []
            for _ in range(2):
                shift, result = 0, 0
                while True:
                    b = ord(encoded[index]) - 63
                    index += 1
                    result |= (b & 0x1F) << shift
                    shift += 5
                    if b < 0x20:
                        break
                deltas.append(~(result >> 1) if result & 1 else result >> 1)
            lat += deltas[0]
            lng += deltas[1]
            points.append((lat / 1e5, lng / 1e5))
    except IndexError:
        return []  # truncated/corrupt polyline
    return points


def middle_point(points):
    """Pin location for a road segment: its middle point, so the pin sits on the road itself."""
    return points[len(points) // 2] if points else (None, None)


def _as_list(raw, *wrapper_keys):
    """APIs sometimes wrap the list in an object. Return the list, or raise if the shape is wrong."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in wrapper_keys:
            if isinstance(raw.get(key), list):
                return raw[key]
    raise ValueError(f"unexpected response shape ({type(raw).__name__})")


def _normalize_each(raw_list, state, build_one):
    """Run build_one on every record, skipping (and logging) the ones that can't become an alert."""
    alerts, skipped = [], 0
    for record in raw_list:
        if not isinstance(record, dict):
            skipped += 1
            continue
        try:
            alert = build_one(record)
        except Exception as e:  # one weird record shouldn't take down the whole state
            log.debug("%s record skipped: %s", state, e)
            alert = None
        if alert is None:
            skipped += 1
        else:
            alerts.append(alert)
    if skipped:
        log.info("%s: skipped %d record(s) with missing or unusable data", state, skipped)
    return alerts


def _alert(state, agency, source_id, title, alert_type, severity, details, location, updated):
    source_id = str(source_id)
    alert_id = source_id if source_id.upper().startswith(f"{state}-") else f"{state}-{source_id}"
    return {
        "alertID": alert_id,
        "location": location,
        "alertType": alert_type,
        "severity": severity,
        "description": f"{title}: {details}" if details else title,
        "lastUpdated": updated,
        "sourceAgency": agency,
        "state": state,
        "title": title,
    }


# ---------- one normalizer per state ----------

# WSDOT's own priority field -> our severity levels
WA_PRIORITY = {"highest": "critical", "high": "high", "medium": "moderate", "low": "low", "lowest": "low"}


def normalize_wa(raw):
    """WSDOT Highway Alerts: incidents with a priority and start/end roadway locations."""

    def build(r):
        start = r.get("StartRoadwayLocation") or {}
        end = r.get("EndRoadwayLocation") or {}
        start_loc = valid_location(start.get("Latitude"), start.get("Longitude"))
        end_loc = valid_location(end.get("Latitude"), end.get("Longitude"))
        if start_loc and end_loc:  # midpoint, like Abby's version
            location = {"latitude": round((start_loc["latitude"] + end_loc["latitude"]) / 2, 6),
                        "longitude": round((start_loc["longitude"] + end_loc["longitude"]) / 2, 6)}
        else:
            location = start_loc or end_loc  # WSDOT sends 0,0 for a missing end point
        if location is None:
            return None

        headline = " ".join(str(pick(r, "HeadlineDescription", "ExtendedDescription", default="")).split())
        category = str(pick(r, "EventCategory", default="")).strip()
        road = str(pick(start, "RoadName", default="") or pick(r, "County", default="")).strip()

        text_sev, text_label = classify(f"{category} {headline}", default_label="Highway Alert")
        priority_sev = WA_PRIORITY.get(str(pick(r, "Priority", default="")).strip().lower(), "low")
        severity = raise_severity(priority_sev, text_sev)  # trust WSDOT, but a closure is always critical

        return _alert(
            "WA", "WA DOT", pick(r, "AlertID", default="unknown"),
            road or "Washington highway",
            category or text_label, severity, headline, location,
            to_iso(pick(r, "LastUpdatedTime", "StartTime")),
        )

    return _normalize_each(_as_list(raw, "Alerts", "alerts"), "WA", build)


def _parse_space_polyline(text):
    """ODOT polylines are plain text: "lat lon lat lon ..." -> [(lat, lon), ...]."""
    values = str(text or "").split()
    if len(values) < 2 or len(values) % 2:
        return []
    try:
        return [(float(values[i]), float(values[i + 1])) for i in range(0, len(values), 2)]
    except ValueError:
        return []


def normalize_or(raw):
    """ODOT TripCheck incidents (WazeSpec): type/subtype, description, and a text polyline."""

    def build(r):
        loc = r.get("location") or {}
        points = _parse_space_polyline(loc.get("polyline"))
        if points:  # midpoint of first and last point, like Abby's version
            (lat1, lng1), (lat2, lng2) = points[0], points[-1]
            location = valid_location((lat1 + lat2) / 2, (lng1 + lng2) / 2)
        else:
            location = valid_location(pick(loc, "latitude", "lat"), pick(loc, "longitude", "lon", "lng"))
        if location is None:
            return None

        incident_type = str(pick(r, "type", default="")).strip().upper()
        subtype = str(pick(r, "subtype", default="")).strip()
        description = " ".join(str(pick(r, "description", default="")).split())
        street = str(pick(loc, "street", default="")).strip()

        severity, label = classify(f"{subtype.replace('_', ' ')} {description}", default_label="Incident")
        if incident_type == "ROAD_CLOSED":
            severity = "critical"
        elif incident_type == "ACCIDENT":
            severity = raise_severity(severity, "moderate")
        # Abby's rule: ODOT says when an incident barely matters
        lowered = f"{subtype} {description}".lower()
        if severity != "critical" and ("minimal delay" in lowered or "minimal impact" in lowered
                                       or "minor" in lowered):
            severity = "low"

        alert_type = incident_type.replace("_", " ").title() if incident_type else label
        return _alert(
            "OR", "OR DOT", pick(r, "id", "incident-id", default="unknown"),
            street or "Oregon highway",
            alert_type, severity, description, location,
            to_iso(pick(r, "updatetime", "creationtime", "starttime")),
        )

    return _normalize_each(_as_list(raw, "incident", "incidents"), "OR", build)


def normalize_id(raw):
    """Idaho 511 winter roads: road segments with an overall condition and encoded polylines."""

    def build(r):
        condition = str(pick(r, "Overall Status", "Primary Condition", default="")).strip()
        if not condition or condition.lower() == "no report":
            return None  # same filter Abby used

        polylines = r.get("EncodedPolyline") or []
        if isinstance(polylines, str):
            polylines = [polylines]
        points = [p for enc in polylines for p in decode_polyline(enc)]
        lat, lng = middle_point(points)
        if lat is None:
            lat, lng = pick(r, "Latitude"), pick(r, "Longitude")
        location = valid_location(lat, lng)
        if location is None:
            return None

        roadway = str(pick(r, "RoadwayName", "Roadway", default="Idaho road segment")).strip()
        where = str(pick(r, "LocationDescription", "AreaName", default="")).strip()
        weather = str(pick(r, "Weather Conditions", "WeatherConditions", default="")).strip()

        severity, label = classify(f"{condition} {weather}", default_label="Road Conditions")
        if condition.lower() in ("closed", "road closed"):
            severity, label = "critical", "Road Closed"
        details = [x for x in (where, condition, weather) if x]
        return _alert(
            "ID", "ID DOT", pick(r, "Id", "ID", default="unknown"),
            roadway, label, severity, ", ".join(details), location,
            to_iso(pick(r, "LastUpdated", "Last Updated")),
        )

    return _normalize_each(_as_list(raw, "data", "winterroads"), "ID", build)
