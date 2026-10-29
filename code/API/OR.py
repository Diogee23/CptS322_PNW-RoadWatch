import os, requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv() # load environment variables from .env file

OR_KEY = os.getenv('OR_API_KEY')




def get_oregon_reports():
    BASE_API_URL = "http://api.odot.state.or.us/tripcheck/RW/Reports?"
    params = {"key": OR_KEY }
    response = requests.get(BASE_API_URL, params=params)
    if response.status_code == 200:
        full_data = response.json()
        return full_data["road-weather-reports"]

def get_oregon_metadata():
    return_list = []
    BASE_API_URL = "http://api.odot.state.or.us/tripcheck/RW/Metadata?"
    params = {"key": OR_KEY }
    response = requests.get(BASE_API_URL, params=params)
    
    if response.status_code == 200:
        full_data = response.json()
        return_list += full_data["road-weather-items"]["weather-condition-list"][4:]
        return_list += full_data["road-weather-items"]["road-condition-list"][2:]
    return return_list

def get_oregon_reports():
    """
    Fetch incident reports from the Oregon DOT API.

    Returns the list of incidents, or an empty list if the
    request fails or the response has an unexpected structure.
    """
    if not OR_KEY:
        print("Error: OR_API_KEY was not found in the .env file.")
        return []

    params = {"key": OR_KEY}
    BASE_API_URL = 'http://api.odot.state.or.us/tripcheck/Incidents/WazeSpec?'
    try:
        response = requests.get(
            BASE_API_URL,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        full_data = response.json()

        # The sample response uses an "incident" list.
        incidents = full_data.get("incident", [])

        if not isinstance(incidents, list):
            print("Error: The API response does not contain a valid incident list.")
            return []

        return incidents

    except requests.RequestException as error:
        print(f"Error fetching Oregon DOT reports: {error}")
        return []
    except ValueError as error:
        print(f"Error decoding Oregon DOT JSON response: {error}")
        return []


def get_oregon_severity(description, incident_type, subtype):
    """
    Assign a basic severity based on incident information.

    These are application-defined rules, not official ODOT
    severity ratings. Adjust them to fit your project.
    """
    description = (description or "").lower()
    incident_type = (incident_type or "").upper()
    subtype = (subtype or "").upper()

    # Incidents that generally warrant high attention
    if (
        incident_type == "ROAD_CLOSED"
        or "road closed" in description
        or "hazardous materials" in description
        or "landslide" in description
    ):
        return "High"

    # Incidents explicitly described as minor or causing
    # minimal traffic impact
    if (
        "minimal delay" in description
        or "minimal impact" in description
        or "minor" in subtype
    ):
        return "Low"

    # Do not assume an unrecognized incident is low severity
    return "Unknown"


def process_oregon_alert(alert):
    """
    Convert one Oregon DOT incident into the shared alert schema.
    """
    location = alert.get("location") or {}

    incident_type = alert.get("type") or "UNKNOWN"
    subtype = alert.get("subtype") or ""
    description = (alert.get("description") or "").strip()
    street = (location.get("street") or "").strip()

    # Normalize the category from the incident type.
    event_category = incident_type.replace("_", " ").title()

    # Combine the road/location with the incident description.
    if street and description:
        headline = f"{street} - {description}"
    else:
        headline = street or description or "No description available"

    # Parse the polyline, which contains alternating latitude
    # and longitude values separated by spaces.
    #
    # Example:
    # "44.727230 -124.057670 44.727230 -124.057670"
    polyline = location.get("polyline") or ""
    values = polyline.split()
    coordinates = None

    if len(values) >= 2 and len(values) % 2 == 0:
        try:
            points = [
                (float(values[i]), float(values[i + 1]))
                for i in range(0, len(values), 2)
            ]

            # Use the midpoint between the first and last points,
            # similar to the Washington DOT normalization approach.
            first_lat, first_lon = points[0]
            last_lat, last_lon = points[-1]

            coordinates = {
                "Latitude": (first_lat + last_lat) / 2,
                "Longitude": (first_lon + last_lon) / 2,
            }

        except ValueError:
            coordinates = None

    # Parse the ISO 8601 update timestamp.
    updated_time = alert.get("updatetime")
    formatted_time = None

    if updated_time:
        try:
            parsed_time = datetime.fromisoformat(updated_time)
            formatted_time = parsed_time.strftime(
                "%Y-%m-%d %H:%M:%S %z"
            )
        except (ValueError, TypeError):
            formatted_time = None

    # Apply the application-defined severity rules.
    severity = get_oregon_severity(
        description,
        incident_type,
        subtype
    )

    return {
        "EventCategory": event_category,
        "HeadlineDescription": headline,
        "Severity": severity,
        "Coordinates": coordinates,
        "LastUpdatedTime": formatted_time,
        "Source": "OR DOT",
    }


def normalize_oregon_data():
    """
    Fetch Oregon DOT incidents and return a list of normalized alerts.
    """
    incidents = get_oregon_reports()

    return [
        process_oregon_alert(incident)
        for incident in incidents
    ]


if __name__ == "__main__":
    normalized_alerts = normalize_oregon_data()

    print(f"Retrieved {len(normalized_alerts)} Oregon DOT alerts.")

    for alert in normalized_alerts[:5]:
        print(alert)
