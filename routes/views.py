
from django.shortcuts import render
import importlib
import inspect as py_inspect
import requests
from django.http import JsonResponse
from .fuel_data import load_fuel_stations
from .fuel_stops import find_fuel_stops
from .geocoding import get_coordinates
import math
from pathlib import Path

import pandas as pd
import requests
from django.http import JsonResponse

# Create your views here.


def test_route_stations(request):
    base_dir = Path(__file__).resolve().parent.parent
    csv_file = base_dir / "data" / "fuel_stations_geocoded_test.csv"

    try:
        stations = pd.read_csv(csv_file)

        # Ruta de prueba: Big Cabin, Oklahoma -> Fort Smith, Arkansas.
        start = (-95.221358, 36.5378651)  # longitud, latitud
        end = (-94.4265011, 35.3880338)

        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start[0]},{start[1]};{end[0]},{end[1]}"
        )

        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return JsonResponse(
                {"error": "OSRM no pudo calcular la ruta"},
                status=502,
            )

        route = data["routes"][0]
        route_points = route["geometry"]["coordinates"]

        # Distancia aproximada entre dos coordenadas, en millas.
        def distance_miles(lon1, lat1, lon2, lat2):
            radius = 3958.8
            lat1, lat2 = math.radians(lat1), math.radians(lat2)
            delta_lat = lat2 - lat1
            delta_lon = math.radians(lon2 - lon1)

            a = (
                math.sin(delta_lat / 2) ** 2
                + math.cos(lat1)
                * math.cos(lat2)
                * math.sin(delta_lon / 2) ** 2
            )

            return 2 * radius * math.asin(min(1, math.sqrt(a)))

        nearby_stations = []

        for _, station in stations.iterrows():
            if pd.isna(station["Latitude"]) or pd.isna(station["Longitude"]):
                continue

          

            station_lon = float(station["Longitude"])
            station_lat = float(station["Latitude"])

            
            nearest_distance = min(
                distance_to_segment_miles(
                    station_lon,
                    station_lat,
                    route_points[i],
                    route_points[i + 1],
                )
                for i in range(len(route_points) - 1)
            )
            if nearest_distance <= 25:
                nearby_stations.append({
                    "OPIS Truckstop ID": str(station["OPIS Truckstop ID"]),
                    "Truckstop Name": station["Truckstop Name"],
                    "City": station["City"],
                    "State": station["State"],
                    "Retail Price": float(station["Retail Price"]),
                    "distance_from_route_miles": round(nearest_distance, 2),
                })

        return JsonResponse({
            "origin": "Big Cabin, OK",
            "destination": "Fort Smith, AR",
            "route_distance_miles": round(
                route["distance"] / 1609.344, 2
            ),
            "route_duration_hours": round(
                route["duration"] / 3600, 2
            ),
            "nearby_stations_count": len(nearby_stations),
            "nearby_stations": nearby_stations,
        })

    except (OSError, ValueError, KeyError, requests.RequestException) as error:
        return JsonResponse({"error": str(error)}, status=500)


def test_fuel_data(request):

    try:
        stations = load_fuel_stations()

        print("Resultado:", type(stations))
        print("Cantidad:", len(stations) if stations is not None else "Es None")

        if stations is None:
            return JsonResponse({
                "error": "load_fuel_stations devolvio None"
            }, status=500)

        return JsonResponse({
            "total_stations": len(stations),
            "columns": stations.columns.tolist(),
            "sample": stations.head(5).to_dict(orient="records"),
        })

    except (OSError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)


def test_geocoding(request):
    try:
        coordinates = get_coordinates(
            "1000 Airport Blvd",
            "Austin",
            "TX",
        )

        if coordinates is None:
            return JsonResponse({
                "error": "No se encontro la direccion"
            }, status=404)

        return JsonResponse(coordinates)

    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=502)
def distance_to_segment_miles(point_lon, point_lat, start, end):
    """
    Distancia aproximada entre una ubicación y un segmento de ruta.
    Las coordenadas de entrada están en longitud, latitud.
    """

    # Convertimos grados a millas aproximadas en una zona local.
    reference_lat = math.radians(point_lat)
    miles_per_degree_lat = 69.0
    miles_per_degree_lon = 69.0 * math.cos(reference_lat)

    px = point_lon * miles_per_degree_lon
    py = point_lat * miles_per_degree_lat

    ax = start[0] * miles_per_degree_lon
    ay = start[1] * miles_per_degree_lat
    bx = end[0] * miles_per_degree_lon
    by = end[1] * miles_per_degree_lat

    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    # Proyectamos el punto sobre el segmento.
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    nearest_x = ax + t * dx
    nearest_y = ay + t * dy

    return math.hypot(px - nearest_x, py - nearest_y)


def calculate_route(request):
    # Solo aceptamos peticiones GET.
    if request.method != "GET":
        return JsonResponse(
            {"error": "Utilizá el método GET"},
            status=405,
        )

    # Obtenemos origen y destino desde los parámetros de la URL.
    origin = request.GET.get("origin", "").strip()
    destination = request.GET.get("destination", "").strip()

    if not origin or not destination:
        return JsonResponse(
            {
                "error": (
                    "Debés indicar origin y destination. "
                    "Ejemplo: ?origin=Austin, TX&destination=Dallas, TX"
                )
            },
            status=400,
        )

    try:
        # Convertimos los nombres de las ubicaciones en coordenadas.
        start = get_coordinates(origin)
        end = get_coordinates(destination)

        if (
            not start
            or not end
            or start["latitude"] is None
            or end["latitude"] is None
        ):
            return JsonResponse(
                {
                    "error": (
                        "No se pudo encontrar el origen o el destino. "
                        "Probá con una ciudad y su estado."
                    )
                },
                status=404,
            )

        # OSRM espera longitud, latitud.
        start_lon = start["longitude"]
        start_lat = start["latitude"]
        end_lon = end["longitude"]
        end_lat = end["latitude"]

        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
        )

        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return JsonResponse(
                {"error": "OSRM no pudo calcular la ruta"},
                status=502,
            )

        route = data["routes"][0]
        fuel_result = find_fuel_stops(
        route["geometry"]["coordinates"]
        )

        if "error" in fuel_result:
            return JsonResponse(fuel_result, status=422)

        return JsonResponse(
            {
                "origin": {
                    "query": origin,
                    "latitude": start_lat,
                    "longitude": start_lon,
                },
                "destination": {
                    "query": destination,
                    "latitude": end_lat,
                    "longitude": end_lon,
                },
                "route_distance_miles": round(
                    route["distance"] / 1609.344, 2
                ),
                "route_duration_hours": round(
                    route["duration"] / 3600, 2
                ),
                

                "fuel_stops": fuel_result["fuel_stops"],
                "fuel_stops_count": fuel_result["fuel_stops_count"],
                "nearby_stations_count": fuel_result["nearby_stations_count"],
                "final_leg_distance_miles": fuel_result["final_leg_distance_miles"],
                "final_gallons_estimated": fuel_result["final_gallons_estimated"],
                "final_fuel_cost_estimated": fuel_result["final_fuel_cost_estimated"],
                "total_gallons_estimated": fuel_result["total_gallons_estimated"],
                "total_fuel_cost_estimated": fuel_result["total_fuel_cost_estimated"],
                "currency": fuel_result["currency"],
            }
        )

    except requests.RequestException as error:
        return JsonResponse(
            {"error": f"Error al consultar un servicio externo: {error}"},
            status=502,
        )
