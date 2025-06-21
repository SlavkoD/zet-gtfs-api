from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import zipfile
import io
import pandas as pd
from threading import Timer

app = FastAPI(title="ZET GTFS API (cached auto-refresh)")

# CORS za frontend pristup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Za razvoj. U produkciji koristi točnu domenu.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GTFS_URL = "https://www.zet.hr/gtfs-scheduled/latest"
gtfs_cache = {}  # Ključ = ime fajla, vrijednost = DataFrame


def refresh_gtfs_cache():
    """Periodički dohvaća i sprema sve GTFS fajlove u memoriju"""
    global gtfs_cache
    try:
        print("🔄 Osvježavanje GTFS cachea...")
        response = requests.get(GTFS_URL)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for file in z.namelist():
                if file.endswith(".txt"):
                    with z.open(file) as f:
                        gtfs_cache[file] = pd.read_csv(f, encoding="utf-8", on_bad_lines="skip")

        print("✅ GTFS cache ažuriran.")
    except Exception as e:
        print("❌ Greška u GTFS cache osvježavanju:", str(e))
    finally:
        Timer(60, refresh_gtfs_cache).start()  # svakih 60 sekundi

# Inicijalizacija pri pokretanju
refresh_gtfs_cache()


def get_file_from_cache(file_name: str) -> pd.DataFrame:
    if file_name not in gtfs_cache:
        raise HTTPException(status_code=404, detail=f"{file_name} nije učitan.")
    return gtfs_cache[file_name].copy()


def df_to_json_clean(df: pd.DataFrame):
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    df = df.fillna("")
    return df.to_dict(orient="records")


@app.get("/")
def root():
    return {"message": "ZET GTFS API radi ✅ (cached)"}


@app.get("/routes")
def get_routes():
    df = get_file_from_cache("routes.txt")
    return df_to_json_clean(df)


@app.get("/stops")
def get_stops():
    df = get_file_from_cache("stops.txt")
    return df_to_json_clean(df)


@app.get("/trips")
def get_trips():
    df = get_file_from_cache("trips.txt")
    return df_to_json_clean(df)


@app.get("/route/{route_id}/stops")
def get_stops_for_route(route_id: str):
    try:
        trips_df = get_file_from_cache("trips.txt")
        stop_times_df = get_file_from_cache("stop_times.txt")
        stops_df = get_file_from_cache("stops.txt")

        trips_for_route = trips_df[trips_df["route_id"] == route_id]
        if trips_for_route.empty:
            raise HTTPException(status_code=404, detail="Nema vožnji za ovu rutu.")

        trip_id = trips_for_route.iloc[0]["trip_id"]
        trip_stops = stop_times_df[stop_times_df["trip_id"] == trip_id].sort_values("stop_sequence")

        stop_ids = trip_stops["stop_id"].tolist()
        stops_info = stops_df[stops_df["stop_id"].isin(stop_ids)].set_index("stop_id")

        result = []
        for _, row in trip_stops.iterrows():
            stop_id = row["stop_id"]
            stop = stops_info.loc[stop_id]
            result.append({
                "stop_id": stop_id,
                "stop_name": stop["stop_name"],
                "arrival_time": row["arrival_time"],
                "departure_time": row["departure_time"],
                "sequence": row["stop_sequence"],
                "lat": stop["stop_lat"],
                "lon": stop["stop_lon"]
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/zip")
def debug_zip():
    return {"sadrzaj_cachea": list(gtfs_cache.keys())}
