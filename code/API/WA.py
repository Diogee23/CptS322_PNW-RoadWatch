import os, requests
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import re

load_dotenv() # load environment variables from .env file

WA_KEY = os.getenv('WA_API_KEY')

def convert_time(date):
    # Extract the timestamp in milliseconds
    match = re.search(r"/Date\((\d+)([+-]\d{4})?\)/", date)

    timestamp_ms = int(match.group(1))

    # Convert milliseconds to seconds and create a datetime
    date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

    # Convert to a readable format
    formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_date

def process_alert(alert):
    # Extract start and end locations
    start = alert["StartRoadwayLocation"]
    end = alert["EndRoadwayLocation"]

    # Calculate average coordinates
    latitude = (start["Latitude"] + end["Latitude"]) / 2
    longitude = (start["Longitude"] + end["Longitude"]) / 2

    # Convert LastUpdatedTime to a readable date
    date_string = alert["LastUpdatedTime"]
    match = re.search(r"/Date\((\d+)([+-]\d{4})?\)/", date_string)

    if not match:
        raise ValueError(f"Invalid date format: {date_string}")
    
    timestamp_ms = int(match.group(1))
    updated_time = datetime.fromtimestamp(
        timestamp_ms / 1000, tz=timezone.utc
    )

    # Preserve the timezone offset supplied by the API
    offset_str = match.group(2)
    if offset_str:
        sign = 1 if offset_str[0] == "+" else -1
        hours = int(offset_str[1:3])
        minutes = int(offset_str[3:5])

        offset = timedelta(hours=hours, minutes=minutes) * sign
        updated_time = updated_time.astimezone(timezone(offset))

    formatted_time = updated_time.strftime("%Y-%m-%d %H:%M:%S %z")

    # Return only the requested fields
    return {
        "EventCategory": alert["EventCategory"],
        "HeadlineDescription": alert["HeadlineDescription"].strip(),
        "Severity": alert["Priority"],
        "Coordinates": {
            "Latitude": latitude,
            "Longitude": longitude
        },
        "LastUpdatedTime": formatted_time,
        "Source": "WA DOT",
    }


def get_washington_weather():
    BASE_API_URL = "http://wsdot.wa.gov/Traffic/api/WeatherInformation/WeatherInformationREST.svc/GetCurrentWeatherInformationAsJson"
    params = {"AccessCode": WA_KEY }
    response = requests.get(BASE_API_URL, params=params)
    if response.status_code == 200:
        full_data = response.json()
        print(full_data)


def get_highway_alerts():
    BASE_API_URL = "https://www.wsdot.wa.gov/Traffic/api/HighwayAlerts/HighwayAlertsREST.svc/GetAlertsAsJson"
    params = {"AccessCode": WA_KEY}
    response = requests.get(BASE_API_URL, params=params)
    try:
        response = requests.get(BASE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Failed to retrieve highway alerts: {exc}")
        return []

def normalize_wa_data():
    return [process_alert(alert) for alert in get_highway_alerts()]

print(normalize_wa_data())