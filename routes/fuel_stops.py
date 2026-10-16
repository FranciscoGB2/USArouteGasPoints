
import math
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
STATIONS_FILE = BASE_DIR / "data" / "fuel_stations_geocoded_test.csv"

MAX_RANGE_MILES = 500
MAX_DISTANCE_FROM_ROUTE_MILES = 5
MPG = 10


def distance_miles(lon1, lat1, lon2, lat2):
    """Distancia aproximada sobre la superficie terrestre."""
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


def project_station(lon, lat, start, end):
    """
    Calcula la distancia de una estación a un segmento
    y su posición aproximada a lo largo de ese segmento.
    """
    reference_lat = math.radians(lat)
    miles_per_degree_lat = 69.0
    miles_per_degree_lon = 69.0 * math.cos(reference_lat)

    px = lon * miles_per_degree_lon
    py = lat * miles_per_degree_lat
    ax = start[0] * miles_per_degree_lon
    ay = start[1] * miles_per_degree_lat
    bx = end[0] * miles_per_degree_lon
    by = end[1] * miles_per_degree_lat

    dx = bx - ax
    dy = by - ay
    segment_length = math.hypot(dx, dy)

    if segment_length == 0:
        return math.hypot(px - ax, py - ay), 0.0

    t = ((px - ax) * dx + (py - ay) * dy) / (
        segment_length ** 2
    )
    t = max(0.0, min(1.0, t))

    nearest_x = ax + t * dx
    nearest_y = ay + t * dy

    distance = math.hypot(px - nearest_x, py - nearest_y)

    return distance, t


def find_fuel_stops(route_coordinates):
    # Cargamos los datos de las estaciones de combustible.
    stations = pd.read_csv(
        STATIONS_FILE,
        dtype={"OPIS Truckstop ID": str},
    )
    # Convertimos las columnas relevantes a valores numéricos y eliminamos filas con datos faltantes.

    stations["Latitude"] = pd.to_numeric(
        stations["Latitude"], errors="coerce"
    )
    stations["Longitude"] = pd.to_numeric(
        stations["Longitude"], errors="coerce"
    )
    stations["Retail Price"] = pd.to_numeric(
        stations["Retail Price"], errors="coerce"
    )

    stations = stations.dropna(
        subset=["Latitude", "Longitude", "Retail Price"]
    )

    # Distancia acumulada a lo largo de la ruta.
    cumulative = [0.0]
    # Calculamos la distancia de cada segmento de la ruta y acumulamos.
    for i in range(len(route_coordinates) - 1):
        lon1, lat1 = route_coordinates[i]
        lon2, lat2 = route_coordinates[i + 1]

        segment_distance = distance_miles(
            lon1, lat1, lon2, lat2
        )
        cumulative.append(cumulative[-1] + segment_distance)

    route_length = cumulative[-1]
    candidates = []

    # Buscamos la distancia mínima de cada estación a la ruta.
    for _, station in stations.iterrows():
        lon = float(station["Longitude"])
        lat = float(station["Latitude"])
        
        best_distance = float("inf")
        # Mejor posición a lo largo de la ruta (en millas) para la estación.
        best_position = None

        for i in range(len(route_coordinates) - 1):
            # Proyectamos la estación sobre el segmento de la ruta.
            distance, fraction = project_station(
                lon,
                lat,
                route_coordinates[i],
                route_coordinates[i + 1],
            )

            if distance < best_distance:
                best_distance = distance

                segment_length = cumulative[i + 1] - cumulative[i]
                best_position = (
                    cumulative[i] + fraction * segment_length
                )

        if (
            # La estación está dentro de la distancia máxima permitida desde la ruta.
            best_distance <= MAX_DISTANCE_FROM_ROUTE_MILES
            and best_position is not None
            and best_position > 0
            and best_position < route_length
        ):
            candidates.append({
                "opis_id": str(station["OPIS Truckstop ID"]),
                "name": str(station["Truckstop Name"]),
                "city": str(station["City"]),
                "state": str(station["State"]),
                "latitude": lat,
                "longitude": lon,
                "retail_price": float(station["Retail Price"]),
                "distance_from_route_miles": round(best_distance, 2),
                "route_position_miles": best_position,
            })

    # Ordenamos las estaciones según su posición en la ruta.
    candidates.sort(key=lambda station: station["route_position_miles"])

    # Eliminamos IDs duplicados.
    unique_candidates = []
    seen_ids = set()

    for station in candidates:
        if station["opis_id"] not in seen_ids:
            unique_candidates.append(station)
            seen_ids.add(station["opis_id"])

    # Elegimos la estación más lejana alcanzable con el tanque lleno.
    stops = []
    current_position = 0.0

    while route_length - current_position > MAX_RANGE_MILES:
        reachable = [
            station
            for station in unique_candidates
            if current_position < station["route_position_miles"]
            <= current_position + MAX_RANGE_MILES
        ]

        if not reachable:
            return {
                "error": (
                    "No hay estaciones candidatas alcanzables "
                    "antes de agotar la autonomía."
                ),
                "route_distance_miles": round(route_length, 2),
                "fuel_stops": stops,
            }

        station = reachable[-1]
        leg_distance = (
            station["route_position_miles"] - current_position
        )

        station["leg_distance_miles"] = round(leg_distance, 2)
        station["gallons_used"] = round(leg_distance / MPG, 2)

        # Costo estimado del combustible consumido en este tramo.
        station["fuel_cost"] = round(
        station["gallons_used"] * station["retail_price"], 2
        )

        stops.append(station)
        current_position = station["route_position_miles"]

        # Calculamos el tramo desde la última parada hasta el destino.
        
            
    # Calcular el tramo final después de la última parada
    final_leg_distance = route_length - current_position
    final_gallons = final_leg_distance / MPG
     
    if stops:
        final_fuel_price = stops[-1]["retail_price"]
    else:
        final_fuel_price = stations["Retail Price"].mean()
     
    final_fuel_cost = final_gallons * final_fuel_price
     

    
    return {
    "route_distance_miles": round(route_length, 2),
    "nearby_stations_count": len(unique_candidates),
    "fuel_stops_count": len(stops),
    "fuel_stops": stops,
    "fuel_economy_mpg": MPG,
    "max_range_miles": MAX_RANGE_MILES,
    "final_leg_distance_miles": round(final_leg_distance, 2),
    "final_gallons_estimated": round(final_gallons, 2),
    "final_fuel_cost_estimated": round(final_fuel_cost, 2),
    "total_gallons_estimated": round(
        sum(stop["gallons_used"] for stop in stops)
        + final_gallons,
        2,
    ),
    "total_fuel_cost_estimated": round(
        sum(stop["fuel_cost"] for stop in stops)
        + final_fuel_cost,
        2,
    ),
    "currency": "USD",
}

