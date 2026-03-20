"""
scripts/download_data.py
Downloads Cricsheet match data (free, no API key needed).

Usage:
    python scripts/download_data.py          # downloads all
    python scripts/download_data.py ipl      # downloads IPL only
    python scripts/download_data.py t20s odis
"""
import os
import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

RAW_DATA_PATH = Path("data/raw")
RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

# Cricsheet dataset URLs (free downloads)
DATASETS = {
    "ipl":   "https://cricsheet.org/downloads/ipl_json.zip",
    "t20s":  "https://cricsheet.org/downloads/t20s_json.zip",
    "odis":  "https://cricsheet.org/downloads/odis_json.zip",
    "tests": "https://cricsheet.org/downloads/tests_json.zip",
}


def download_and_extract(name: str, url: str):
    extract_path = RAW_DATA_PATH / name

    if extract_path.exists() and any(extract_path.glob("*.json")):
        print(f"[{name}] Already downloaded ({len(list(extract_path.glob('*.json')))} files). Skipping.")
        return

    print(f"[{name}] Downloading from Cricsheet...")
    zip_path = RAW_DATA_PATH / f"{name}.zip"

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    with open(zip_path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=name) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    print(f"[{name}] Extracting...")
    extract_path.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_path)

    zip_path.unlink()
    json_count = len(list(extract_path.glob("*.json")))
    print(f"[{name}] Done. {json_count} match files ready.")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(DATASETS.keys())
    for name in targets:
        if name in DATASETS:
            download_and_extract(name, DATASETS[name])
        else:
            print(f"[ERROR] Unknown dataset: {name}. Options: {list(DATASETS.keys())}")
