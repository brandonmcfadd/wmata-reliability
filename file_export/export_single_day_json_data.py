"""interacts with PowerBi API to query for a specific days arrival data"""
import os
import json
from time import sleep  # Used to retrieve secrets in .env file
from datetime import datetime
from dateutil import tz
from dotenv import load_dotenv  # Used to Load Env Var
import requests  # Used for API Calls
from azure.identity import ClientSecretCredential

# Load .env variables
load_dotenv()

microsoft_client_id = os.getenv('MICROSOFT_CLIENT_ID')
microsoft_tenant_id = os.getenv('MICROSOFT_TENANT_ID')
microsoft_client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
microsoft_workspace_id = os.getenv('MICROSOFT_WORKSPACE_ID')
main_file_path = os.getenv('WMATA_FILE_PATH')
wmata_dataset_id = os.getenv('WMATA_DATASET_ID')

main_file_path_json = main_file_path + "train_arrivals/json/"


def get_date(date_type):
    """formatted date shortcut"""
    if date_type == "short":
        date = datetime.strftime(datetime.now(), "%Y%m%d")
    elif date_type == "hour":
        date = datetime.strftime(datetime.now(), "%H")
    elif date_type == "long":
        date = datetime.strftime(datetime.now(), "%Y-%m-%dT%k:%M:%SZ")
    return date


def get_token():
    """gets token for PBI service to make API calls under service principal"""
    scope = 'https://analysis.windows.net/powerbi/api/.default'
    client_secret_credential_class = ClientSecretCredential(
        tenant_id=microsoft_tenant_id, client_id=microsoft_client_id, client_secret=microsoft_client_secret)
    access_token_class = client_secret_credential_class.get_token(scope)
    token_string = access_token_class.token
    return token_string


def get_report_data(dataset, days_old):
    """makes api call to PBI service to extract data from dataset"""
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{microsoft_workspace_id}/datasets/{dataset}/executeQueries"

    payload = json.dumps({
        "queries": [
            {
                "query": f"EVALUATE FILTER(date_range,date_range[Days Old]={days_old})"
            }
        ],
        "serializerSettings": {
            "includeNulls": True
        }
    })
    headers = {
        'Authorization': f"Bearer {bearer_token}",
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "POST", url, headers=headers, data=payload, timeout=360)
    response_json = json.loads(response.text)

    try:
        return (response_json['results'][0].get('tables')[0].get('rows'))
    except:  # pylint: disable=bare-except
        print("error in:", response_json)


def get_last_refresh_time(dataset):
    """grabs the last dataset refresh time to add to the files"""
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{microsoft_workspace_id}/datasets/{dataset}/refreshes?$top=1"

    headers = {
        'Authorization': f"Bearer {bearer_token}",
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", url, headers=headers, timeout=360)
    response_json = json.loads(response.text)
    try:
        end_time = response_json['value'][0].get('endTime')
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz('America/Chicago')
        utc = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        utc = utc.replace(tzinfo=from_zone)
        cst = utc.astimezone(to_zone)
        cst_string = datetime.strftime(cst, "%Y-%m-%dT%H:%M:%S%z")
        return cst_string
    except:  # pylint: disable=bare-except
        print("error in:", response_json)


def parse_response_wmata(data, last_refresh, days_old):
    """takes the data from the API and prepares it to add to JSON output"""
    system_total, system_scheduled, system_scheduled_remaining = 0, 0, 0
    routes_information = {}
    for item in data:
        shortened_date = item["date_range[Dates]"][:10]
        integrity_actual = item["date_range[Integrity - Actual]"]
        integrity_percent = item["date_range[Integrity - Percentage]"]
        system_total += item["date_range[Actual Arrivals]"]
        if item["date_range[Scheduled Arrivals]"] is not None:
            system_scheduled += item["date_range[Scheduled Arrivals]"]
        if item["date_range[Remaining Scheduled]"] is not None:
            system_scheduled_remaining += item["date_range[Remaining Scheduled]"]
        if item["date_range[Arrivals Percentage]"] is None:
            arrival_percentage = 0
        else:
            arrival_percentage = item["date_range[Arrivals Percentage]"]
        single_route_information = [item["date_range[Actual Arrivals]"], item["date_range[Scheduled Arrivals]"], arrival_percentage,
                                    item["date_range[Remaining Scheduled]"], item["date_range[Consistent Headways]"], item["date_range[Longest Wait]"],
                                    item["date_range[On-Time Trains]"]]
        routes_information[item["date_range[Route]"]
                           ] = single_route_information
    json_file = main_file_path_json + shortened_date + ".json"
    try:
        system_percent = system_total/system_scheduled
    except: # pylint: disable=bare-except
        system_percent = 0
    file_data = {
        "Data Provided By": "Brandon McFadden - http://api.brandonmcfadden.com",
        "Reports Acccessible At": "https://brandonmcfadden.com/wmata-reliability",
        "API Information At": "http://api.brandonmcfadden.com",
        "Entity": "wmata",
        "Date": shortened_date,
        "LastUpdated": last_refresh,
        "IntegrityChecksPerformed": integrity_actual,
        "IntegrityPercentage": integrity_percent,
        "system": {
            "ActualRuns": system_total,
            "ScheduledRuns": system_scheduled,
            "ScheduledRunsRemaining": system_scheduled_remaining,
            "PercentRun": system_percent
        },
        "routes": {
            "Blue": {
                "ActualRuns": routes_information["Blue"][0],
                "ScheduledRuns": routes_information["Blue"][1],
                "PercentRun": routes_information["Blue"][2],
                "RemainingScheduled": routes_information["Blue"][3],
                "Consistent_Headways": routes_information["Blue"][4],
                "LongestWait": routes_information["Blue"][5],
                "Trains_On_Time": routes_information["Blue"][6]
            },
            "Green": {
                "ActualRuns": routes_information["Green"][0],
                "ScheduledRuns": routes_information["Green"][1],
                "PercentRun": routes_information["Green"][2],
                "RemainingScheduled": routes_information["Green"][3],
                "Consistent_Headways": routes_information["Green"][4],
                "LongestWait": routes_information["Green"][5],
                "Trains_On_Time": routes_information["Green"][6]
            },
            "Orange": {
                "ActualRuns": routes_information["Orange"][0],
                "ScheduledRuns": routes_information["Orange"][1],
                "PercentRun": routes_information["Orange"][2],
                "RemainingScheduled": routes_information["Orange"][3],
                "Consistent_Headways": routes_information["Orange"][4],
                "LongestWait": routes_information["Orange"][5],
                "Trains_On_Time": routes_information["Orange"][6]
            },
            "Red": {
                "ActualRuns": routes_information["Red"][0],
                "ScheduledRuns": routes_information["Red"][1],
                "PercentRun": routes_information["Red"][2],
                "RemainingScheduled": routes_information["Red"][3],
                "Consistent_Headways": routes_information["Red"][4],
                "LongestWait": routes_information["Red"][5],
                "Trains_On_Time": routes_information["Red"][6]
            },
            "Silver": {
                "ActualRuns": routes_information["Silver"][0],
                "ScheduledRuns": routes_information["Silver"][1],
                "PercentRun": routes_information["Silver"][2],
                "RemainingScheduled": routes_information["Silver"][3],
                "Consistent_Headways": routes_information["Silver"][4],
                "LongestWait": routes_information["Silver"][5],
                "Trains_On_Time": routes_information["Silver"][6]
            },
            "Yellow": {
                "ActualRuns": routes_information["Yellow"][0],
                "ScheduledRuns": routes_information["Yellow"][1],
                "PercentRun": routes_information["Yellow"][2],
                "RemainingScheduled": routes_information["Yellow"][3],
                "Consistent_Headways": routes_information["Yellow"][4],
                "LongestWait": routes_information["Yellow"][5],
                "Trains_On_Time": routes_information["Yellow"][6]
            }
        }
    }

    with open(json_file, 'w', encoding="utf-8") as f:
        print(f"Remaining: {days_old} | Saving Data In: {json_file}")
        json.dump(file_data, f, indent=2)


bearer_token = get_token()

remaining = 2
last_refresh_time = None

while last_refresh_time is None:
    last_refresh_time = get_last_refresh_time(wmata_dataset_id)
    if last_refresh_time is None:
        print("Last Refresh Time is not available, sleeping 60 seconds")
        sleep(60)

while remaining >= 0:
    try:
        parse_response_wmata(get_report_data(
            wmata_dataset_id, remaining), last_refresh_time, remaining)
    except:  # pylint: disable=bare-except
        print("Failed to grab WMATA #", remaining)
    remaining -= 1
    sleep(1)
