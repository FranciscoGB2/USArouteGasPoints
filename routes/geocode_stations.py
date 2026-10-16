
import time
from pathlib import Path

import pandas as pd

from .fuel_data import load_fuel_stations
from .geocoding import get_coordinates


def geocode_stations():
    base_dir = Path(__file__).resolve().parent.parent
    output_file = base_dir / "data" / "fuel_stations_geocoded_test.csv"

    # Cargamos todas las estaciones del archivo original.
    stations = load_fuel_stations()
    stations = stations.drop_duplicates(
        subset=["OPIS Truckstop ID"]
    ).copy()

    # Si ya existe un archivo de resultados, continuamos desde ahí.
    if output_file.exists():
        previous_results = pd.read_csv(output_file)

        if "OPIS Truckstop ID" in previous_results.columns:
            processed_ids = set(
                previous_results["OPIS Truckstop ID"].dropna().astype(str)
            )
            results = previous_results.to_dict(orient="records")
        else:
            processed_ids = set()
            results = []
    else:
        processed_ids = set()
        results = []

    # Excluimos las estaciones que ya figuran en los resultados.
    stations["OPIS Truckstop ID"] = (
        stations["OPIS Truckstop ID"].astype(str)
    )

    pending = stations[
        ~stations["OPIS Truckstop ID"].isin(processed_ids)
    ]

    total = len(stations)
    already_processed = total - len(pending)
    total_pending = len(pending)

    print(f"Total de estaciones: {total}")
    print(f"Ya procesadas: {already_processed}")
    print(f"Pendientes: {total_pending}")

    bar_width = 30
    processed_now = 0

    for _, station in pending.iterrows():
        try:
            coordinates = get_coordinates(
                station["Address"],
                station["City"],
                station["State"],
            )

            results.append({
                "OPIS Truckstop ID": station["OPIS Truckstop ID"],
                "Truckstop Name": station["Truckstop Name"],
                "Address": station["Address"],
                "City": station["City"],
                "State": station["State"],
                "Retail Price": station["Retail Price"],
                "Latitude": coordinates["latitude"] if coordinates else None,
                "Longitude": coordinates["longitude"] if coordinates else None,
                "Match Type": (
                    coordinates["match_type"] if coordinates else "not_found"
                ),
                "Matched Location": (
                    coordinates["display_name"] if coordinates else ""
                ),
            })

        except Exception as error:
            print(
                f"\nError en {station['City']}, "
                f"{station['State']}: {error}"
            )

            # Registramos el fallo para no detener todo el proceso.
            results.append({
                "OPIS Truckstop ID": station["OPIS Truckstop ID"],
                "Truckstop Name": station["Truckstop Name"],
                "Address": station["Address"],
                "City": station["City"],
                "State": station["State"],
                "Retail Price": station["Retail Price"],
                "Latitude": None,
                "Longitude": None,
                "Match Type": "error",
                "Matched Location": "",
            })

        processed_now += 1

        # Guardamos un checkpoint cada 25 estaciones.
        if processed_now % 25 == 0:
            pd.DataFrame(results).to_csv(output_file, index=False)

        # Barra de progreso.
        progress = processed_now / total_pending if total_pending else 1
        filled = int(bar_width * progress)
        progress_bar = "#" * filled + "-" * (bar_width - filled)

        print(
            f"\rProgreso: [{progress_bar}] "
            f"{processed_now}/{total_pending} ({progress:.1%})"
            f" - {station['City']}, {station['State']}",
            end="\n" if processed_now == total_pending else "\r",
            flush=True,
            )

        # Pausa entre estaciones para limitar las consultas.
        time.sleep(1.1)

    if total_pending:
        print()

    # Guardamos también las últimas estaciones, aunque sean menos de 25.
    pd.DataFrame(results).to_csv(output_file, index=False)

    print(f"\nArchivo generado: {output_file}")
    print(f"Estaciones en el archivo de resultados: {len(results)}")


if __name__ == "__main__":
    geocode_stations()
