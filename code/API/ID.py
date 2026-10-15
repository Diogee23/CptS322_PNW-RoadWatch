import os, requests
from dotenv import load_dotenv

load_dotenv() # load environment variables from .env file

ID_KEY = os.getenv('ID_API_KEY')

def get_idaho_weather():
    BASE_API_URL = "https://511.idaho.gov/api/v3/get/winterroads"
    params = {"key": ID_KEY }
    response = requests.get(BASE_API_URL, params=params)
    print(response)
    if response.status_code == 200:
        parsed_data = []
        full_data = response.json()
        for item in range(len(full_data)):
            if full_data[item]["Weather Conditions"] != 'null' and full_data[item]["Weather Conditions"] != None:
                parsed_data.append(full_data[item])
                parsed_data[-1]["EncodedPolyline"] = ""
        print(parsed_data)

get_idaho_weather()