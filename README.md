# USAroute — Fuel Stop API

## Overview

USAroute is a Django REST-style API that calculates driving routes between locations in the United States and identifies fuel stations along the route.

The application uses OSRM to obtain driving routes and a geocoded fuel station dataset to identify candidate stops.

## Features

- Accepts origin and destination locations.
- Geocodes locations into geographic coordinates.
- Calculates driving distance and estimated duration.
- Identifies fuel stations near the route.
- Selects fuel stops based on a maximum range of 500 miles.
- Estimates fuel consumption and fuel costs using an assumed fuel economy of 10 MPG.
- Returns route information and fuel stop details in JSON format.

## Technologies

- Python
- Django
- pandas
- OSRM Routing API
- Geocoding service
- CSV dataset of fuel stations

## Requirements

- Python installed.
- Dependencies listed in `requirements.txt`.
- The fuel station dataset in the expected `data/` directory.
- Internet access to query the external routing and geocoding services.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/FranciscoGB2/USArouteGasPoints.git
   cd USAroute
   ```

2. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Activate the environment.

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

## API Usage

**Method:** `GET`

**Endpoint:**

```text
http://127.0.0.1:8000/api/route/
```

**Query parameters:**

- `origin`: starting location in the United States.
- `destination`: destination location in the United States.

**Example request:**

```text
http://127.0.0.1:8000/api/route/?origin=Miami,%20FL&destination=Fort%20Lauderdale,%20FL
```

The API returns JSON containing route information, fuel stops, and estimated fuel consumption and costs.

## Fuel Stop Assumptions

- Maximum driving range per tank: 500 miles.
- Fuel economy: 10 miles per gallon.
- Fuel stations are considered when they are within 5 miles of the route.
- Fuel costs are estimates based on the dataset's retail prices.
- Route distances and station positions are approximate calculations.

## Testing

The endpoint can be tested with Postman by sending a `GET` request with `origin` and `destination` query parameters.

Example:

```text
http://127.0.0.1:8000/api/route/?origin=Los%20Angeles,%20CA&destination=Dallas,%20TX
```

## Limitations

- Routing and geocoding depend on external services.
- Fuel station availability and prices depend on the provided dataset.
- Estimated fuel costs do not necessarily represent actual expenses.
- Stations may require detours that are not fully reflected in the route-distance estimate.

## Author

Francisco Gonzalez Bonorino
