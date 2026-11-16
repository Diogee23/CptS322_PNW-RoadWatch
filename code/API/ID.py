import os, requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import polyline

load_dotenv() # load environment variables from .env file

ID_KEY = os.getenv('ID_API_KEY')

def get_severity(condition):
    condition = (condition or "").strip().lower()

    severity_map = {
        "dry": "low",
        "wet": "moderate",
        "icy patches": "high",
    }

    return severity_map.get(condition, "Unknown")

def get_idaho_weather():
    BASE_API_URL = "https://511.idaho.gov/api/v3/get/winterroads"
    params = {"key": ID_KEY }
    try:
        response = requests.get(BASE_API_URL, params=params, timeout=15)
    
        if response.status_code == 200:
            parsed_data = []
            full_data = response.json()
            EXCLUDED_STATUSES = {"no report", "dry"}

            for item in full_data:
                status = (item.get("Overall Status") or "").strip().lower()
                if status not in EXCLUDED_STATUSES:
                    parsed_data.append(item)
            return parsed_data
        else:
            return []
    except requests.RequestException as error:
            print(f"Error fetching Idaho DOT reports: {error}")
            return []
    except ValueError as error:
        print(f"Error decoding Idaho DOT JSON response: {error}")
        return []

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
            "latitude": sum(lat for lat, lon in points) / len(points),
            "longitude": sum(lon for lat, lon in points) / len(points),
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
        "alertID": str(alert.get("Id")),
        "alertType": "Road Conditions",
        "severity": severity,
        "description": headline,
        "location": coordinates,
        "sourceAgency": "ID DOT",
        "lastUpdated": formatted_time,
    }

def normalize_idaho_data():
    return [process_idaho_alert(alert) for alert in get_idaho_weather()]

if __name__ == "__main__":
    normalized_alerts = normalize_idaho_data()

    print(f"Retrieved {len(normalized_alerts)} Idaho DOT alerts.")

    for alert in normalized_alerts[:5]:
        print(alert)