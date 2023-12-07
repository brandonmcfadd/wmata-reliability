# Washington Metropolitan Area Transit Authority ("WMATA") Reliability Tracker

## Overview
This project (and associated PowerBi Report) was created to help provide insight and transparency into the current service levels of the Washington Metropolitan Area Transit Authority ("WMATA") rail network. Utilizing the WMATA API, it can be determined when a train arrives at a specific circuit along the line. Using this data, the number of arrivals can be determined and compared to the number scheduled via the GTFS feed of published schedules. This project is a rebuild off of my previous project for [CTA Reliability](https://github.com/brandonmcfadd/cta-reliability).

## Station Selection 
The station selected along each line is one where all trains, regardless of destination, will arrive and is as close to the center of the line as feasible.

### The following stations were selected to monitor each of the 6 WMATA Lines in operation:
* Red - Judiciary Square
    * Glenmont
    * Shady Grove
* Orange - L'Enfant Plaza
    * New Carrollton
    * Vienna
* Blue - L'Enfant Plaza
    * Franconia-Springfield
    * Downtown Largo
* Green - L'Enfant Plaza
    * Branch Ave
    * Greenbelt
* Yellow - L'Enfant Plaza
    * Huntington
    * Mt Vernon Sq
* Silver - L'Enfant Plaza
    * Ashburn
    * Downtown Largo


## Equipment
* I use a Google Cloud Compute E2 Micro to run the program 24/7, however the program can be run on theoretically anything capable of running Python scripts.

## Installation
* Create API access token on the [WMATA developer site](https://developer.wmata.com) 
* Clone the repository on your endpoint of choice with the following `git clone https://github.com/brandonmcfadd/wmata-reliability.git`
* Change into the working directory of the cloned repository `cd wmata-reliability`
* Install the required dependencies `pip install -r requirements.txt`

## Configuration
* Enable the portions you want to use by changing False to True in the `settings.json` file
* To change the station being monitored modify the Station/Stop Information `circuit-ids` in the `settings.json` file with the circuit code(s) you want to use.
* WMATA Circuit codes can be found on [WMATA Developer site](https://developer.wmata.com/docs/services/5763fa6ff91823096cac1057/operations/57641afc031f59363c586dca?) using the WMATA Standard Routes API.

## Enviornment File
* You'll need to create a .env file in your directory to safely store your secrets.
    * Don't forget to add your .env file to your .gitignore list and never check application secrets, usernames or passwords into a GitHub repo! 
* The following entries are required in your .env file:
    ```
    WMATA_PRIMARY_KEY = 'insert key here'
    WMATA_FILE_PATH = 'full file path/wmata-reliability'
    ```

## Running the program
* Once you have everything [Installed](#Installation) and [Configured](#Configuration) Run the main program `python3 main.py`

## Power Bi Report
* You can view the PowerBi Report displaying the data I have collected at:<br>[brandonmcfadden.com/cta-reliability](https://brandonmcfadden.com/wmata-reliability)