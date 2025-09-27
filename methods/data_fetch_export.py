import os
import garth
import datetime
import csv
from types import SimpleNamespace

device = SimpleNamespace()
data = []
# today = datetime.date.today()
date_pointer = None
rows_list = []
today = datetime.date(2024, 12, 28)


# Gets garmin device info
def garmin_info():
    # get garmin device name
    url = "/web-gateway/device-info/primary-training-device"
    device_data = garth.connectapi(url)
    
    device_name = device_data["RegisteredDevices"][0]["displayName"]
    epoch_ms  = device_data["RegisteredDevices"][0]["registeredDate"]
    registered_date = datetime.datetime.fromtimestamp(epoch_ms / 1000.0)
    
    # comment out profile_image_uuid to avoid error in garth init.py
    display_name = garth.UserProfile.get().display_name
    
    print("Connected to", device_name)

    device.device_name = device_name
    device.registered_date = registered_date.date()
    device.display_name = display_name


def append_latest():
        
        with open("garmin_data.csv", "r") as f:
            rows = list(csv.reader(f))

        # remove last metrics row to avoid incomplete data
        rows = rows[:-1]

        if rows:
            last_row = rows[-1]
            last_date_str = last_row[0]

            # parse date
            try:
                last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
                print("Last entry in CSV on:", last_date)

                #set date_pointer to next day
                date_pointer = last_date + datetime.timedelta(days=1)

                print(f"Appending data from {date_pointer} to {today}")
                return date_pointer, rows
            except ValueError:
                print("Could not parse date:", last_date_str)
        

def fetch_export_metrics():
    global rows_list
    #see if garmin_data.csv exists, if yes, load it and get the last date
    if os.path.exists("garmin_data.csv"):
        print("garmin_data.csv found, do you want to append new metrics? (y/n)")
        choice = input().strip().lower()
        if choice == 'y':
            date_pointer, rows_list = append_latest()     
            print(len(rows_list), "rows loaded from existing CSV.")

        else:
            print("Exited")
            date_pointer = device.registered_date
            
    else:
        print("Fetching all data from registered date.")
        date_pointer = device.registered_date

    # fetch daily metrics from registered date to today
    print("Appending data from", date_pointer, "to", today) 

    total_days = (today - date_pointer).days
    day_count = 0

    while date_pointer <= today:
        day_count += 1

        #daily summary metrics
        daily_summary_url = f'/usersummary-service/usersummary/daily/{device.display_name}'
        daily_summary_params = {"calendarDate": str(date_pointer.isoformat())}
        daily_summary_data = garth.connectapi(daily_summary_url, params=daily_summary_params)

        #sleep data
        sleep_url = f"/wellness-service/wellness/dailySleepData/{device.display_name}"
        sleep_params = {"date": str(date_pointer.isoformat()), "nonSleepBufferMinutes": 60}
        sleep_data = garth.connectapi(sleep_url, params=sleep_params)

        #these metrics are prone to availability errors - hence the fallback mechanisms
        try:
            avgOvernightHrv = sleep_data["avgOvernightHrv"]
        except KeyError:
            avgOvernightHrv = None
        
        try:
            avgSleepStress = sleep_data["dailySleepDTO"]["avgSleepStress"]
        except KeyError:
            avgSleepStress = None

        try:
            restingHeartRate = sleep_data["restingHeartRate"]
        except KeyError:
            restingHeartRate = None

        sleep_score = (
                sleep_data.get("dailySleepDTO", {})
              .get("sleepScores", {})
              .get("overall", {})
              .get("value")
        )

        #hrv data
        hrv_url = f"/hrv-service/hrv/{str(date_pointer.isoformat())}"
        hrv_data = garth.connectapi(hrv_url)

        def safe_get(data, *keys, default=None):
            """Safely access nested dictionary keys."""
            if data is None:
                return default
            
            current = data
            for key in keys:
                if not isinstance(current, dict):
                    return default
                current = current.get(key, default)
                if current is None:
                    return default
            return current

        daily_metric = {
            "date":date_pointer,
            "steps":daily_summary_data["totalSteps"],
            "calories":daily_summary_data["totalKilocalories"],
            "body_battery":daily_summary_data["bodyBatteryHighestValue"],
            
            "sleep_duration":daily_summary_data["sleepingSeconds"],
            "sleep_score":sleep_score,
            "sleep_hrv":avgOvernightHrv,
            "sleep_deep":sleep_data["dailySleepDTO"]["deepSleepSeconds"],
            "sleep_rem":sleep_data["dailySleepDTO"]["remSleepSeconds"],
            "sleep_light":sleep_data["dailySleepDTO"]["lightSleepSeconds"],
            "sleep_stress":avgSleepStress,
            "resting_heart_rate":restingHeartRate,
            
            # Safe dictionary access with get() method
            "weekly_avg_hrv": safe_get(hrv_data, "hrvSummary", "weeklyAvg"),
            "hrv_baseline_low": safe_get(hrv_data, "hrvSummary", "baseline", "balancedLow"),
            "hrv_baseline_high": safe_get(hrv_data, "hrvSummary", "baseline", "balancedUpper"),
            "hrv_status": safe_get(hrv_data, "hrvSummary", "status"),

            "moderate_intensity_minutes":daily_summary_data["moderateIntensityMinutes"],
            "vigorous_intensity_minutes":daily_summary_data["vigorousIntensityMinutes"],
            
            "stress":daily_summary_data["averageStressLevel"],
            "resting_stress":daily_summary_data["restStressDuration"],
            "low_stress":daily_summary_data["lowStressDuration"],
            "medium_stress":daily_summary_data["mediumStressDuration"],
            "high_stress":daily_summary_data["highStressDuration"],
            "stress_status":daily_summary_data["stressQualifier"],
        }


        # progress
        progress = (day_count / total_days) * 100
        print(f"Progress: {progress:.2f}% ({day_count}/{total_days} days)")

        # save metric
        data.append(daily_metric)

        # increment
        date_pointer += datetime.timedelta(days=1)



def export_to_csv():

    if len(rows_list) > 0:
        with open("garmin_data.csv", "w", newline="") as file:
            writer = csv.writer(file)
            print("rows list length - ", len(rows_list))
            writer.writerows(rows_list)

        with open("garmin_data.csv", "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writerows(data)
    
    else:
        with open("garmin_data.csv", "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


    print("Garmin data exported to CSV file successfully")