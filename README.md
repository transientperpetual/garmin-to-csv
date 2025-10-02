# Garmin Data Exporter

This app lets you download health and activity data from your Garmin device and save it into a CSV file.  

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

<img width="4167" height="1766" alt="dfd" src="https://github.com/user-attachments/assets/a8872c6e-e7a6-4954-b23a-d0e5590c2bd1" />

## Features
- Connects to your Garmin account.
- Fetches daily metrics including steps, calories, sleep, HRV, stress, and more.
- Exports the data into a CSV file (`garmin_data.csv`).
- Option to append new metrics to an existing file or start fresh.

## Requirements
- Python 3.8+
- Garmin authentication via [`garth`](https://pypi.org/project/garth/)

## Usage

#### 1. Clone this repository

```bash
git clone https://github.com/transientperpetual/garmin-to-csv.git
cd garmin-to-csv
```

#### 2. Create and activate virtual env

```bash
python -m venv venv
source venv/bin/activate # On Windows: .venv\Scripts\activate
```

#### 3. Install dependencies via requirements.txt

```bash
pip install -r requirements.txt
```

#### 4. Run main.py  

```bash
python main.py
```

##### 5. To append new data to existing csv file place the file in the root dir and select "y" when prompted to append new metrics to the file.
