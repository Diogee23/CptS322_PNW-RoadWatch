import os, requests
from dotenv import load_dotenv

load_dotenv() # load environment variables from .env file

OR_KEY = os.getenv('OR_API_KEY')

def get_oregon_reports():
    BASE_API_URL = "http://api.odot.state.or.us/tripcheck/RW/Reports?"
    params = {"key": OR_KEY }
    response = requests.get(BASE_API_URL, params=params)
    if response.status_code == 200:
        full_data = response.json()
        print(len(full_data["road-weather-reports"]))

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

MetaData = get_oregon_metadata()
print(MetaData)
## get_oregon_reports()
