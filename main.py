import garth
from methods.auth import authenticate
from methods.data_fetch_export import garmin_info, fetch_export_metrics, export_to_csv
import csv

# Authenticate user
authenticate()

# Data export filters and tranformations
garmin_info()

# Fetch  data
fetch_export_metrics()

#Export data
export_to_csv()





