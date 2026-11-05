"""Unit tests for normalize.py: severity rules, bad records, timestamps, coordinates, per-state formats."""

import pytest

from normalize import (classify, decode_polyline, middle_point, normalize_id, normalize_or,
                       normalize_wa, to_iso, valid_location)


@pytest.mark.parametrize("text, severity, label", [
    ("Road closed", "critical", "Road Closed"),
    ("US 2 is closed in both directions", "critical", "Road Closed"),
    ("Closed", "critical", "Road Closed"),
    ("Right lane closed for paving", "moderate", "Lane Closure"),
    ("Collision blocking the right lane", "moderate", "Lane Closure"),
    ("Rest area closed", "high", "Closure"),
    ("Carry chains or traction tires", "high", "Chains Required"),
    ("Landslide on the shoulder", "high", "Hazard"),
    ("Black ice reported", "high", "Ice"),
    ("Icy Patches", "high", "Ice"),
    ("Blowing snow", "high", "Heavy Snow"),
    ("Snowing", "moderate", "Snow"),
    ("Dense fog", "moderate", "Low Visibility"),
    ("Two-car crash", "moderate", "Collision"),
    ("Wet", "moderate", "Wet Roads"),
    ("Dry", "low", "Conditions Report"),
    ("", "low", "Conditions Report"),
    (None, "low", "Conditions Report"),
    ("Police on scene, service road", "low", "Conditions Report"),  # "ice" inside other words shouldn't count
])
def test_classify(text, severity, label):
    assert classify(text) == (severity, label)


def test_to_iso_formats():
    assert to_iso("/Date(1792080000000-0700)/") == "2026-10-15T16:00:00+00:00"
    assert to_iso(1792080000) == "2026-10-15T16:00:00+00:00"
    assert to_iso(1792080000000) == "2026-10-15T16:00:00+00:00"  # milliseconds
    assert to_iso("2026-10-15T16:00:00Z") == "2026-10-15T16:00:00+00:00"
    assert to_iso("2026-10-15T09:00:00-07:00") == "2026-10-15T16:00:00+00:00"
    assert to_iso(None) is None
    assert to_iso("not a date") is None


def test_valid_location():
    assert valid_location(47.4, -121.4) == {"latitude": 47.4, "longitude": -121.4}
    assert valid_location("47.4", "-121.4") is not None  # numbers as strings are fine
    assert valid_location(None, -121.4) is None
    assert valid_location(0, 0) is None
    assert valid_location(-121.4, 47.4) is None  # swapped lat/lng
    assert valid_location("abc", -121.4) is None


def test_decode_polyline():
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")  # Google's documented example
    assert [(round(a, 3), round(b, 3)) for a, b in pts] == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    assert decode_polyline("") == []
    assert decode_polyline("_p~") == []  # truncated
    assert middle_point(pts) == pts[1]
    assert middle_point([]) == (None, None)


# ---------- WA: WSDOT Highway Alerts ----------

def wa_alert(**over):
    a = {"AlertID": 1, "Priority": "Medium", "EventCategory": "Maintenance",
         "HeadlineDescription": "Shoulder work", "LastUpdatedTime": "/Date(1792080000000-0700)/",
         "StartRoadwayLocation": {"RoadName": "SR 270", "Latitude": 46.73, "Longitude": -117.18},
         "EndRoadwayLocation": {"RoadName": "SR 270", "Latitude": 46.71, "Longitude": -117.04}}
    a.update(over)
    return a


def test_wa_basic_fields_and_midpoint():
    [a] = normalize_wa([wa_alert()])
    assert a["alertID"] == "WA-1" and a["alertType"] == "Maintenance"
    assert a["severity"] == "moderate"  # WSDOT "Medium"
    assert a["location"] == {"latitude": 46.72, "longitude": -117.11}
    assert a["description"] == "SR 270: Shoulder work"
    assert a["sourceAgency"] == "WA DOT"


@pytest.mark.parametrize("priority, expected", [("Highest", "critical"), ("High", "high"),
                                                ("Low", "low"), ("Lowest", "low"), ("???", "low")])
def test_wa_priority_mapping(priority, expected):
    assert normalize_wa([wa_alert(Priority=priority)])[0]["severity"] == expected


def test_wa_closure_text_beats_low_priority():
    [a] = normalize_wa([wa_alert(Priority="Low", HeadlineDescription="Highway closed due to fire")])
    assert a["severity"] == "critical"


def test_wa_missing_end_point_uses_start():
    [a] = normalize_wa([wa_alert(EndRoadwayLocation={"Latitude": 0, "Longitude": 0})])
    assert a["location"] == {"latitude": 46.73, "longitude": -117.18}


def test_wa_bad_records_are_skipped_not_fatal():
    raw = [wa_alert(AlertID=1), wa_alert(AlertID=2, StartRoadwayLocation=None, EndRoadwayLocation=None),
           wa_alert(AlertID=3, LastUpdatedTime="garbage"), "not even a dict"]
    alerts = normalize_wa(raw)
    assert [a["alertID"] for a in alerts] == ["WA-1", "WA-3"]
    assert alerts[1]["lastUpdated"] is None


# ---------- OR: ODOT Incidents (WazeSpec) ----------

def or_incident(**over):
    i = {"id": "123", "type": "HAZARD", "subtype": "", "description": "Debris in roadway",
         "location": {"street": "I-5", "polyline": "44.0 -123.0 44.2 -123.2"},
         "updatetime": "2026-10-15T09:00:00-07:00"}
    i.update(over)
    return i


def test_or_basic_fields_and_midpoint():
    [a] = normalize_or({"incident": [or_incident()]})
    assert a["alertID"] == "OR-123" and a["alertType"] == "Hazard"
    assert a["location"] == {"latitude": 44.1, "longitude": -123.1}
    assert a["lastUpdated"] == "2026-10-15T16:00:00+00:00"
    assert a["severity"] == "moderate"  # debris


def test_or_road_closed_is_critical():
    assert normalize_or([or_incident(type="ROAD_CLOSED", description="Detour in place")])[0]["severity"] == "critical"


def test_or_minimal_delay_is_low():
    [a] = normalize_or([or_incident(type="ACCIDENT", description="Crash, expect minimal delay")])
    assert a["severity"] == "low"


def test_or_accident_is_at_least_moderate():
    assert normalize_or([or_incident(type="ACCIDENT", description="Vehicle off road")])[0]["severity"] == "moderate"


def test_or_bad_polyline_is_skipped():
    raw = [or_incident(id="1"), or_incident(id="2", location={"polyline": "44.0 -123.0 44.2"}),
           or_incident(id="3", location={"polyline": "abc def"}), or_incident(id="4", location=None)]
    assert [a["alertID"] for a in normalize_or(raw)] == ["OR-1"]


def test_or_id_not_double_prefixed():
    assert normalize_or([or_incident(id="OR-55")])[0]["alertID"] == "OR-55"


# ---------- ID: Idaho 511 Winter Roads ----------

def id_road(**over):
    r = {"Id": 7, "RoadwayName": "US-95", "LocationDescription": "Lewiston Grade",
         "Overall Status": "Wet", "LastUpdated": 1792082000,
         "EncodedPolyline": ["_p~iF~ps|U_ulLnnqC_mqNvxq`@"]}
    r.update(over)
    return r


def test_id_basic_fields():
    # Google's example polyline goes outside the PNW box, so use a local one
    [a] = normalize_id([id_road(EncodedPolyline=None, Latitude=46.44, Longitude=-116.96)])
    assert a["alertID"] == "ID-7" and a["severity"] == "moderate"
    assert a["description"] == "US-95: Lewiston Grade, Wet"
    assert a["lastUpdated"] == "2026-10-15T16:33:20+00:00"


def test_id_skips_no_report():
    assert normalize_id([id_road(**{"Overall Status": "No Report"}, Latitude=46.4, Longitude=-117)]) == []


def test_id_closed_is_critical_even_with_weather():
    [a] = normalize_id([id_road(**{"Overall Status": "Closed", "Weather Conditions": "Blowing snow"},
                                EncodedPolyline=None, Latitude=44.35, Longitude=-115.21)])
    assert a["severity"] == "critical" and a["alertType"] == "Road Closed"


def test_id_polyline_list_or_string():
    enc = "sxsaHzbafUs]k~H"  # a short segment near I-90 in north Idaho
    for value in ([enc], enc):
        [a] = normalize_id([id_road(EncodedPolyline=value)])
        assert a["location"]["latitude"] == pytest.approx(47.6, abs=0.1)


def test_unexpected_shape_raises_valueerror():
    with pytest.raises(ValueError):
        normalize_or("<html>error page</html>")
    with pytest.raises(ValueError):
        normalize_wa({"Message": "Invalid AccessCode"})
    with pytest.raises(ValueError):
        normalize_id(None)
