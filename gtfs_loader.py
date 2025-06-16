import requests
import zipfile
import io
import pandas as pd
import os

GTFS_URL = "https://www.zet.hr/gtfs-scheduled/latest"
EXTRACT_DIR = "data"


def download_and_extract_gtfs():
    response = requests.get(GTFS_URL)
    if response.status_code != 200:
        raise Exception("Failed to download GTFS data.")

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(EXTRACT_DIR)


def load_gtfs_file(file_name):
    path = os.path.join(EXTRACT_DIR, file_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{file_name} not found in extracted data.")

    return pd.read_csv(path)
