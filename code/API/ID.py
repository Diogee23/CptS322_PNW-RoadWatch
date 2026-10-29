import os, requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import polyline

load_dotenv() # load environment variables from .env file

ID_KEY = os.getenv('ID_API_KEY')

def get_severity(condition):
    condition = (condition or "").strip().lower()

    severity_map = {
        "dry": "Low",
        "wet": "Medium",
        "icy patches": "High",
    }

    return severity_map.get(condition, "Unknown")

def get_idaho_weather():
    BASE_API_URL = "https://511.idaho.gov/api/v3/get/winterroads"
    params = {"key": ID_KEY }
    response = requests.get(BASE_API_URL, params=params)
    ##print(response)
    if response.status_code == 200:
        parsed_data = []
        full_data = response.json()
        for item in range(len(full_data)):
            if full_data[item]["Overall Status"] != "No Report":
                parsed_data.append(full_data[item])
        return parsed_data

def process_idaho_alert(alert):
    # Extract and decode the route
    encoded_polylines = alert.get("EncodedPolyline") or []

    points = [
        point
        for encoded in encoded_polylines
        for point in polyline.decode(encoded)
    ]

    # Calculate average coordinates
    coordinates = None

    if points:
        coordinates = {
            "Latitude": sum(lat for lat, lon in points) / len(points),
            "Longitude": sum(lon for lat, lon in points) / len(points),
        }

    # Extract road condition and map severity
    condition = alert.get("Overall Status") or "Unknown"
    severity = get_severity(condition)

    # Build headline with condition
    roadway = alert.get("RoadwayName") or "Unknown roadway"
    location = alert.get("LocationDescription") or "Location unavailable"

    headline = f"{roadway}: {location} - {condition}"

    # Format last updated time
    last_updated = alert.get("LastUpdated")

    formatted_time = (
        datetime.fromtimestamp(last_updated, tz=timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S %z")
        if last_updated is not None
        else None
    )
    return {
        "EventCategory": "Road Conditions",
        "HeadlineDescription": headline,
        "Severity": severity,
        "Coordinates": coordinates,
        "LastUpdatedTime": formatted_time,
        "Source": "ID DOT",
    }

def normalize_idaho_data():
    return [process_idaho_alert(alert) for alert in get_idaho_weather()]

data = normalize_idaho_data()
print(data)
print(len(data))