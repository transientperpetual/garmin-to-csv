import garth
from methods.auth import authenticate
from methods.data_fetch_export import GarminDataFetcher, CSVExporter
import csv
import os

def main():
    #Authenticate user
    authenticate()

    fetcher = GarminDataFetcher()
    fetcher.connect_device()

# Decide if appending or starting fresh
    append_existing = input("Append existing CSV data? (y/n): ").strip().lower() == "y"

    metrics = fetcher.fetch_metrics(append_existing=append_existing)

    exporter = CSVExporter("garmin_data.csv")
    exporter.export(metrics, fetcher.rows_list)

if __name__ == "__main__":
    main()





