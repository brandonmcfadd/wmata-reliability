"""wmata-reliability by Brandon McFadden - Github: https://github.com/brandonmcfadd/wmata-reliability"""
import os  # Used to retrieve secrets in .env file
import logging
from logging.handlers import RotatingFileHandler
import json  # Used for JSON Handling
import time  # Used to Get Current Time
# Used for converting Prediction from Current Time
from datetime import datetime, timedelta
from csv import DictWriter
from dotenv import load_dotenv  # Used to Load Env Var
from google.cloud import bigquery
from google.oauth2 import service_account
import requests  # Used for API Calls
import urllib3
urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
except AttributeError:
    pass  # no pyopenssl support used / needed / available


# Load .env variables
load_dotenv()

# ENV Variables
train_api_key = os.getenv('WMATA_PRIMARY_KEY')
main_file_path = os.getenv('WMATA_FILE_PATH')
train_arrivals_table = os.getenv('WMATA_TRAIN_ARRIVALS_TABLE')
integrity_check_table = os.getenv('WMATA_INTEGRITY_CHECK_TABLE')
google_credentials_file = main_file_path + "credentials/cta-utilities-410023-73a50f35625b.json"

# Logging Information
LOG_FILENAME = main_file_path + 'logs/wmata-reliability.log'
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10e6, backupCount=10)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)

# Constants
integrity_file_csv_headers = ['Full_Date_Time', 'Simple_Date_Time', 'Status']
train_arrivals_csv_headers = ['Full_Date_Time', 'Train_ID', 'Train_Number', 'Car_Count',
                              'Direction_Num', 'Circuit_ID', 'Destination_Station_Code', 'Line_Code',
                              'Seconds_At_Location', 'Service_Type']


def get_date(date_type):
    """formatted date shortcut"""
    if date_type == "short":
        date = datetime.strftime(datetime.now(), "%Y%m%d")
    elif date_type == "hour":
        date = datetime.strftime(datetime.now(), "%H")
    elif date_type == "api-today":
        date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    elif date_type == "api-yesterday":
        date = datetime.strftime(datetime.now()-timedelta(days=1), "%Y-%m-%d")
    elif date_type == "now":
        date = datetime.strftime(
            datetime.now()+timedelta(hours=1), "%Y-%m-%dT%H:%M:%S")
    elif date_type == "short-now":
        date = datetime.strftime(datetime.now()+timedelta(hours=1), "%H:%M:%S")
    elif date_type == "current-month":
        date = datetime.strftime(datetime.now(), "%b%Y")
    return date


def train_api_call_to_wmata_api():
    """Gotta talk to the wmata and get Train Times"""
    logging.info(
        "Making Main Secure URL WMATA Train API Call:")
    try:
        headers = {
            'api_key': train_api_key
        }
        api_response = requests.get(
            train_tracker_positions_url_api, timeout=10, headers=headers)
        add_train_to_file_api(api_response.json())
        api_response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        logging.error("Main URL - Http Error: %s", errh)
    except requests.exceptions.ConnectionError as errc:
        logging.error("Main URL - Error Connecting: %s", errc)
    except requests.exceptions.Timeout as errt:
        logging.error("Main URL - Timeout Error: %s", errt)
    except requests.exceptions.RequestException as err:
        logging.error("Main URL - Error in API Call to Train Tracker: %s", err)
    return api_response


def add_train_to_file_api(trains):
    """Parses API Result from Train Tracker API and adds ETA's to a list"""
    for train in trains["TrainPositions"]:
        if train["CircuitId"] in train_station_circuit_ids and train["ServiceType"] == "Normal" and int(train["SecondsAtLocation"] < 60):
            current_month = get_date("current-month")
            now = get_date("now")
            file_path = main_file_path + "train_arrivals/train_arrivals-" + \
                str(current_month) + ".csv"
            with open(file_path, 'a', newline='', encoding='utf8') as csvfile:
                writer_object = DictWriter(
                    csvfile, fieldnames=train_arrivals_csv_headers)
                writer_object.writerow({'Full_Date_Time': now, 'Train_ID': train["TrainId"], 'Train_Number': train["TrainNumber"], 'Car_Count': train["CarCount"],
                                        'Direction_Num': train["DirectionNum"], 'Circuit_ID': train["CircuitId"], 'Destination_Station_Code': train["DestinationStationCode"], 'Line_Code': train["LineCode"],
                                        'Seconds_At_Location': train["SecondsAtLocation"], 'Service_Type': train["ServiceType"]})
            rows_to_insert.append({'Full_Date_Time': now, 'Train_ID': train["TrainId"], 'Train_Number': train["TrainNumber"], 'Car_Count': train["CarCount"],
                                        'Direction_Num': train["DirectionNum"], 'Circuit_ID': train["CircuitId"], 'Destination_Station_Code': train["DestinationStationCode"], 'Line_Code': train["LineCode"],
                                        'Seconds_At_Location': train["SecondsAtLocation"], 'Service_Type': train["ServiceType"]})


def check_main_train_file_exists():
    """Used to check if file exists"""
    current_month = get_date("current-month")
    file_path = main_file_path + "train_arrivals/train_arrivals-" + \
        str(current_month) + ".csv"
    train_csv_file = os.path.exists(file_path)
    if train_csv_file is False:
        logging.info(
            "Main Train File Doesn't Exist...Creating File and Adding Headers...")
        with open(file_path, 'w+', newline='', encoding='utf8') as csvfile:
            writer_object = DictWriter(
                csvfile, fieldnames=train_arrivals_csv_headers)
            writer_object.writeheader()
    else:
        logging.info("Main Train File Exists...Continuing...")


def check_integrity_file_exists():
    """Used to check if file exists"""
    current_month = get_date("current-month")
    file_path = main_file_path + "train_arrivals/integrity-check-" + \
        str(current_month) + ".csv"
    integrity_csv_file = os.path.exists(file_path)
    if integrity_csv_file is False:
        logging.info(
            "Integrity File Doesn't Exist...Creating File and Adding Headers...")
        with open(file_path, 'w+', newline='', encoding='utf8') as csvfile:
            writer_object = DictWriter(
                csvfile, fieldnames=integrity_file_csv_headers)
            writer_object.writeheader()
    else:
        logging.info("Integrity File Exists...Continuing...")


def add_integrity_file_line(status):
    """Used to check if file exists"""
    current_month = datetime.strftime(datetime.now(), "%b%Y")
    current_simple_time = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M")
    current_long_time = datetime.strftime(
        datetime.now(), "%Y-%m-%dT%H:%M:%S.%f%z")
    file_path = main_file_path + "train_arrivals/integrity-check-" + \
        str(current_month) + ".csv"
    with open(file_path, 'a', newline='', encoding='utf8') as csvfile:
        writer_object = DictWriter(
            csvfile, fieldnames=integrity_file_csv_headers)
        writer_object.writerow({'Full_Date_Time': current_long_time,
                               'Simple_Date_Time': current_simple_time, 'Status': status})
    row_to_insert = [{'Full_Date_Time': current_long_time,
                      'Simple_Date_Time': current_simple_time, 'Status': status}]
    add_rows_to_bigquery(row_to_insert, integrity_check_table)

def add_rows_to_bigquery(row, table_id):
    """Takes a Row as Input and inserts it to the specified Google Big Query Table"""
    credentials = service_account.Credentials.from_service_account_file(
        google_credentials_file, scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    client = bigquery.Client(credentials=credentials, project=credentials.project_id,)

    errors = client.insert_rows_json(table_id, row)  # Make an API request.
    if errors:
        logging.error("Encountered errors while inserting rows: %s", errors)
    else:
        logging.info(
            "Successfully Inserted Row Into Table %s: %s", table_id, row)



logging.info("Welcome to TrainTracker, WMATA Edition!")
# Check to make sure output file exists and write headers
while True:  # Where the magic happens
    check_main_train_file_exists()
    # check_backup_train_file_exists()
    check_integrity_file_exists()
    # Settings
    file = open(file=main_file_path + 'settings.json',
                mode='r',
                encoding='utf-8')
    settings = json.load(file)

    # API URL's
    train_tracker_url_api = settings["train-tracker"]["api-url"]
    train_tracker_positions_url_api = settings["train-tracker"]["positions-url"]

    # Variables for Settings information - Only make settings changes in the settings.json file
    enable_train_tracker_api = settings["train-tracker"]["api-enabled"]
    train_station_map_ids = settings["train-tracker"]["station-ids"]
    train_station_circuit_ids = settings["train-tracker"]["circuit-ids"]

    current_time = get_date("now")
    current_time_console = "The Current Time is: " + get_date("short-now")
    logging.info(current_time_console)

    # API Portion runs if enabled and station id's exist
    rows_to_insert = []

    logging.info("Currently Operating Under Standard Map IDs")
    if train_station_circuit_ids != "" and enable_train_tracker_api == "True":
        try:
            response1 = train_api_call_to_wmata_api()
        except:  # pylint: disable=bare-except
            logging.critical("Failure to Check For Trains :(")

    if rows_to_insert:
            add_rows_to_bigquery(rows_to_insert, train_arrivals_table)


    add_integrity_file_line("Success")

    # Wait and do it again
    SLEEP_AMOUNT = 30
    SLEEP_STRING = "Sleeping " + str(SLEEP_AMOUNT) + " Seconds"
    logging.info(SLEEP_STRING)
    time.sleep(SLEEP_AMOUNT)
