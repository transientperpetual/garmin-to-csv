import garth
import datetime
import csv
from types import SimpleNamespace

device = SimpleNamespace()
data = []
today = datetime.date.today()
# today = datetime.date(2024, 12, 26)


def garmin_info():
    # get garmin device name
    url = "/web-gateway/device-info/primary-training-device"
    device_data = garth.connectapi(url)
    
    device_name = device_data["RegisteredDevices"][0]["displayName"]
    epoch_ms  = device_data["RegisteredDevices"][0]["registeredDate"]
    registered_date = datetime.datetime.fromtimestamp(epoch_ms / 1000.0)
    
    # comment out profile_image_uuid to avoid error in gath init.py
    display_name = garth.UserProfile.get().display_name
    
    print("Garmin authentication successful.",device_name, registered_date, display_name)

    device.device_name = device_name
    device.registered_date = registered_date.date()
    device.display_name = display_name



def fetch_export_metrics():

    #sync fresh
    if True:
        date_pointer = device.registered_date
    #sync latest
    else:
        #get the last date of sync and set it + 1 as date_pointer.
        # date_pointer = device.metrics.latest('date').date + datetime.timedelta(days=1)
        # print("Garmin last sync date - ", device.metrics.latest('date').date, " will begin sync from ", date_pointer)
        print("")
    
    total_days = (today - date_pointer).days
    day_count = 0

    while date_pointer < today:
        day_count += 1

        #daily summary metrics
        daily_summary_url = f'/usersummary-service/usersummary/daily/{device.display_name}'
        daily_summary_params = {"calendarDate": str(date_pointer.isoformat())}
        daily_summary_data = garth.connectapi(daily_summary_url, params=daily_summary_params)

        #your day is presumed to start with sleep and sleep hrv
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
    with open("output.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print("Garmin data exported to CSV file successfully")