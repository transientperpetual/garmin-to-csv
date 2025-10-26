import os, csv, datetime, garth
from datetime import date, time
from types import SimpleNamespace
from collections import OrderedDict

class GarminDataFetcher:
    def __init__(self):
        self.device = SimpleNamespace()
        self.data = []
        self.rows_list = []
        self.today = datetime.date.today()
        # self.today = datetime.date(2025, 4, 10)

    def connect_device(self):
        url = "/web-gateway/device-info/primary-training-device"
        device_data = garth.connectapi(url)

        reg = device_data["RegisteredDevices"][0]
        self.device.device_name = reg["displayName"]
        self.device.registered_date = datetime.datetime.fromtimestamp(reg["registeredDate"] / 1000).date()
        self.device.display_name = garth.UserProfile.get().display_name

        print("Connected to", self.device.device_name)

    # Could not find date wise activity fetching url. Hence going this way. 
    def activity_metrics(self):
        url = "/activitylist-service/activities/search/activities"
        start = 0              # activity latest date offset
        limit = 999         # number of activities to fetch

        params = {"start": str(start), "limit": str(limit)}
        detailed_activities = garth.connectapi(url, params=params)

        if detailed_activities is None:
            print("No activities data received")
            return []
        
        #filter out inessential details
        activities = []

        for activity in detailed_activities:
            activity_when = ""
            activity_time = datetime.datetime.strptime(activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S").time()
            if activity_time > time(4,30) and activity_time <= time(10,30):
                activity_when = "Morning"
            elif activity_time > time(10,30) and activity_time <= time(16,30):
                activity_when = "Afternoon"
            elif activity_time > time(16,30) and activity_time <= time(19,30):
                activity_when = "Evening"
            else:
                activity_when = "Night"

            # round off numbers

            activity_subset = {
            "activityId" : activity["activityId"], 
            "Name" : activity["activityName"],
            "Start Time" : activity["startTimeLocal"], 
            "Activity When": activity_when,
            "Type" : activity["activityType"]["typeKey"],
            "Distance" : activity.get("distance"),
            "Duration" : round(activity["duration"]),
            "Elapsed Duration": round(activity["elapsedDuration"]),
            "Moving Duration" : activity.get("movingDuration"),
            "Average Speed": activity.get("averageSpeed"),
            "Mean Cadence": activity.get("averageRunningCadenceInStepsPerMinute", 0), 
            "Calories": activity.get("calories"),
            "Mean HR": activity.get("averageHR"),
            "Max HR": activity.get("maxHR"),
            "Steps" : activity.get("steps"),
            "Aerobic TE": activity.get("aerobicTrainingEffect"),
            "Anaerobic TE": activity.get("anaerobicTrainingEffect"),
            "Water Loss": activity.get("waterEstimated"),
            "Training Load": activity.get("activityTrainingLoad"),
            "Zone 1 Time": activity.get("hrTimeInZone_1"),
            "Zone 2 Time": activity.get("hrTimeInZone_2"),
            "Zone 3 Time": activity.get("hrTimeInZone_3"),
            "Zone 4 Time": activity.get("hrTimeInZone_4"),
            "Zone 5 Time": activity.get("hrTimeInZone_5"),
            } 

            activities.append(activity_subset)

            activities.sort(key=lambda x: datetime.datetime.strptime(x["Start Time"], "%Y-%m-%d %H:%M:%S"))

            # NOTE:
            # For multiple activities in the day, the one with more calories will be chosen for the general day metrics.
            # More suitable methods can be devised if one frequently registers more than 1 activity in a day (this is rare for me).

        # # Get headers from the keys of the first activity
        # headers = activities[0].keys()

        # with open("garmin_activities.csv", mode="w", newline="", encoding="utf-8") as file:
        #     writer = csv.DictWriter(file, fieldnames=headers)
        #     writer.writeheader()
        #     writer.writerows(activities)

        # print(f"Saved {len(activities)} activities to ")

        return activities


    def all_data(self):
        daily_metrics = self.fetch_metrics()       # list of dicts with "Date"
        activity_metrics = self.activity_metrics() # list of dicts with "Start Time" + "Calories"

        # Filter activities -> one per day (highest calories)
        filtered_activities = {}
        for activity in activity_metrics:
            current_date = datetime.datetime.strptime(activity["Start Time"], "%Y-%m-%d %H:%M:%S").date()
            cal = activity.get("Calories") or 0
            if (current_date not in filtered_activities or 
                cal > (filtered_activities[current_date].get("Calories") or 0)):
                filtered_activities[current_date] = activity

        primary_activities = list(filtered_activities.values())

        # Make lookup by date
        activity_by_date = {
            datetime.datetime.strptime(a["Start Time"], "%Y-%m-%d %H:%M:%S").date(): a
            for a in primary_activities
        }

        # Merge daily metrics + activities
        merged_data = []
        for d in daily_metrics:
            date_val = d["Date"]
            if isinstance(date_val, str):
                date_obj = datetime.datetime.strptime(date_val, "%Y-%m-%d").date()
            else:
                date_obj = date_val

            merged = OrderedDict(d)  # preserve field order from daily_metrics
            activity = activity_by_date.get(date_obj)
            if activity:
                for k, v in activity.items():
                    if k not in merged:  # only add new keys at the end
                        merged[k] = v
            merged_data.append(merged)

        # Build fieldnames (keep natural order)
        fieldnames = list(merged_data[0].keys())
        for row in merged_data[1:]:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        # Fill missing fields
        for row in merged_data:
            for fn in fieldnames:
                row.setdefault(fn, "")

        # Write to CSV
        with open("all_metrics.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(merged_data)

        print(f"Merged data saved to all_metrics.csv with {len(merged_data)} rows.")
        

    def fetch_metrics(self, append_existing=False, filename="garmin_data.csv"):
        if append_existing and os.path.exists(filename):
            start_date, self.rows_list = self.existing_metrics(filename)
            start_date += datetime.timedelta(days=1)  # start from the next day
        else:
            start_date = self.device.registered_date
            print("Fetching all data from registered date: ", start_date)

        total_days = (self.today - start_date).days + 1

        for i, day in enumerate(range(total_days), start=1):
            date = start_date + datetime.timedelta(days=day)
            daily_metric = self._fetch_daily_metric(date)
            if daily_metric:
                self.data.append(daily_metric)

            print(f"Progress: {i/total_days:.2%} ({i}/{total_days} days)")

        return self.data

    
    def existing_metrics(self, filename):
        with open(filename, "r") as f:
            rows = list(csv.reader(f))[:-1]  # drop last row (avoid possible incompleteness)

        if not rows:
            return self.device.registered_date, []

        last_date = datetime.datetime.strptime(rows[-1][0], "%Y-%m-%d").date()
        return last_date, rows


    def _safe_get(self, data, *keys, default=None):
        for key in keys:
            if not isinstance(data, dict):
                return default
            data = data.get(key, default)
        return data
    
    def _fetch_daily_metric(self, date):
        try:
            summary_url = f'/usersummary-service/usersummary/daily/{self.device.display_name}'
            sleep_url = f"/wellness-service/wellness/dailySleepData/{self.device.display_name}"
            hrv_url = f"/hrv-service/hrv/{date}"

            daily_summary = garth.connectapi(summary_url, params={"calendarDate": str(date)})
            sleep = garth.connectapi(sleep_url, params={"date": str(date), "nonSleepBufferMinutes": 60})
            hrv = garth.connectapi(hrv_url)

            return {
                "Date": date,
                "Steps": daily_summary.get("totalSteps"),
                "Calories": daily_summary.get("totalKilocalories"),
                "Body Battery": daily_summary.get("bodyBatteryHighestValue"),
                "Sleep Duration": daily_summary.get("sleepingSeconds"),
                "Sleep Score": self._safe_get(sleep, "dailySleepDTO", "sleepScores", "overall", "value"),
                "Sleep HRV": sleep.get("avgOvernightHrv"),
                "Sleep Deep": self._safe_get(sleep, "dailySleepDTO", "deepSleepSeconds"),
                "Sleep REM": self._safe_get(sleep, "dailySleepDTO", "remSleepSeconds"),
                "Sleep Light": self._safe_get(sleep, "dailySleepDTO", "lightSleepSeconds"),
                "Sleep Stress": self._safe_get(sleep, "dailySleepDTO", "avgSleepStress"),
                "RHR": sleep.get("restingHeartRate"),
                "Weekly avg. HRV": self._safe_get(hrv, "hrvSummary", "weeklyAvg"),
                "HRV Baseline Low": self._safe_get(hrv, "hrvSummary", "baseline", "balancedLow"),
                "HRV Baseline High": self._safe_get(hrv, "hrvSummary", "baseline", "balancedUpper"),
                "HRV Status": self._safe_get(hrv, "hrvSummary", "status"),
                "Moderate Intensity Minutes": daily_summary.get("moderateIntensityMinutes"),
                "Vigorous Intensity Minutes": daily_summary.get("vigorousIntensityMinutes"),
                "Stress": daily_summary.get("averageStressLevel"),
                "Resting Stress": daily_summary.get("restStressDuration"),
                "Low Stress": daily_summary.get("lowStressDuration"),
                "Med Stress": daily_summary.get("mediumStressDuration"),
                "High Stress": daily_summary.get("highStressDuration"),
                "Stress Status": daily_summary.get("stressQualifier"),
            }
        except Exception as e:
            print(f"Failed to fetch metrics for {date}: {e}")
            return None
        
class CSVExporter:
    def __init__(self, filename):
        self.filename = filename

    def export(self, data, rows_list):
        mode = "w" if rows_list else "a"
        with open(self.filename, mode, newline="") as f:
            if rows_list:
                csv.writer(f).writerows(rows_list)

        with open(self.filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            if not rows_list:
                writer.writeheader()
            writer.writerows(data)

        print("Garmin data exported successfully.")