from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FUEL_FILE = BASE_DIR / "data"/ "fuel-prices-for-be-assessment.csv"

def load_fuel_stations():
    stations = pd.read_csv(FUEL_FILE)
    expected_columns = ["OPIS Truckstop ID",
        "Truckstop Name",
        "Address",
        "City",
        "State",
        "Rack ID",
        "Retail Price",
    ]
    missing_columns = [

        column
        for column in expected_columns
        if column not in stations.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing expected columns in fuel data: {missing_columns}")

    stations["Retail Price"] = pd.to_numeric(stations["Retail Price"], errors="coerce")
    stations = stations.dropna(subset=["City", "State", "Retail Price"])
    return stations