import os, requests
from dotenv import load_dotenv

load_dotenv() # load environment variables from .env file

WA_KEY = os.getenv('WA_API_KEY')

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
    if response.status_code == 200:
        full_data = response.json()
        print(full_data)
        return full_data
    else:
        print(f"Request failed with status {response.status_code}: {response.text}")

get_highway_alerts()