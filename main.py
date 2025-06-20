from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import zipfile
import io
import pandas as pd

app = FastAPI(title="ZET GTFS API (live ZIP access)")

# ✅ Dodaj CORS middleware (dozvoljava pozive s frontend aplikacije)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 možeš kasnije ograničiti na npr. http://localhost:3000
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
            print("ZIP datoteke:", z.namelist())

            if file_name not in z.namelist():
                raise HTTPException(status_code=404, detail=f"{file_name} nije pronađen u GTFS zipu.")

            with z.open(file_name) as f:
                return pd.read_csv(f, encoding="utf-8", on_bad_lines="skip")  # sigurnije čitanje
    except Exception as e:
        print("Greška pri čitanju:", str(e))
        raise HTTPException(status_code=500, detail=f"Greška: {str(e)}")

def df_to_json_clean(df: pd.DataFrame):
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    df = df.fillna("")
    return df.to_dict(orient="records")

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

@app.get("/")
def root():
    return {"message": "ZET GTFS API radi!"}

@app.get("/debug/zip")
def debug_zip():
    try:
        response = requests.get(GTFS_URL)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            return {"sadrzaj_zipa": z.namelist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
