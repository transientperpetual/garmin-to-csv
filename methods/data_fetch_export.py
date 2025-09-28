import os, csv, datetime, garth
from types import SimpleNamespace

class GarminDataFetcher:
    def __init__(self):
        self.device = SimpleNamespace()
        self.data = []
        self.rows_list = []
        # self.today = datetime.date.today()
        self.today = datetime.date(2025, 1, 18)

    def connect_device(self):
        url = "/web-gateway/device-info/primary-training-device"
        device_data = garth.connectapi(url)

        reg = device_data["RegisteredDevices"][0]
        self.device.device_name = reg["displayName"]
        self.device.registered_date = datetime.datetime.fromtimestamp(reg["registeredDate"] / 1000).date()
        self.device.display_name = garth.UserProfile.get().display_name

        print("Connected to", self.device.device_name)


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
                # help me clear the last row 

        with open(self.filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            if not rows_list:
                writer.writeheader()
            writer.writerows(data)

        print("Garmin data exported successfully.")