import garth
from methods.auth import authenticate
from methods.data_fetch_export import GarminDataFetcher, CSVExporter
import csv
import os
import json

def main():
    ## Authenticate user
    authenticate()

    fetcher = GarminDataFetcher()
    fetcher.connect_device()

    ## Allow fetching only metrics or activities or both.
    ## Make the appending function compatible for "both" option. Not needed for "activities" option as all activities get fetched on the single request.
    
    ## FETCH ALL
    # all_data = fetcher.all_data()

    ## FETCH ACTIVITIES ONLY
    # metrics = fetcher.activity_metrics()

    ## FETCH METRICS ONLY
    ## Decide if appending or starting fresh
    append_existing = input("Append existing CSV data? (y/n): ").strip().lower() == "y"
    metrics = fetcher.fetch_metrics(append_existing=append_existing)

    exporter = CSVExporter("garmin_data.csv")
    exporter.export(metrics, fetcher.rows_list)

if __name__ == "__main__":
    main()





