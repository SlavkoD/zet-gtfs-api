from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import zipfile
import io
import pandas as pd

app = FastAPI(title="ZET GTFS API (live ZIP access)")

# ✅ CORS za razvoj
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # U produkciji: npr. ["https://mojfrontend.hr"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GTFS_URL = "https://www.zet.hr/gtfs-scheduled/latest"


def read_gtfs_file_from_zip(file_name: str) -> pd.DataFrame:
    try:
        response = requests.get(GTFS_URL)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            if file_name not in z.namelist():
                raise HTTPException(status_code=404, detail=f"{file_name} nije pronađen.")
            with z.open(file_name) as f:
                return pd.read_csv(f, encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Greška: {str(e)}")


def df_to_json_clean(df: pd.DataFrame):
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    df = df.fillna("")
    return df.to_dict(orient="records")


@app.get("/")
def root():
    return {"message": "ZET GTFS API radi!"}


@app.get("/routes")
def get_routes():
    df = read_gtfs_file_from_zip("routes.txt")
    return df_to_json_clean(df)


@app.get("/stops")
def get_stops():
    df = read_gtfs_file_from_zip("stops.txt")
    return df_to_json_clean(df)


@app.get("/trips")
def get_trips():
    df = read_gtfs_file_from_zip("trips.txt")
    return df_to_json_clean(df)


@app.get("/debug/zip")
def debug_zip():
    try:
        response = requests.get(GTFS_URL)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            return {"sadrzaj_zipa": z.namelist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/route/{route_id}/stops")
def get_stops_for_route(route_id: str):
    try:
        trips_df = read_gtfs_file_from_zip("trips.txt")
        stop_times_df = read_gtfs_file_from_zip("stop_times.txt")
        stops_df = read_gtfs_file_from_zip("stops.txt")

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
