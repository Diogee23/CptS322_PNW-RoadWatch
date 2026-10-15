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

get_washington_weather()
        