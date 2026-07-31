"""
Download candidate Kaggle datasets for RailLens - run this LOCALLY on your own
machine (the sandbox this assistant runs in can't reach kaggle.com either).

Setup (one time):
    pip install kaggle

Auth (one time): the kaggle package looks for credentials in one of two places:
    1. Environment variables KAGGLE_USERNAME and KAGGLE_KEY, OR
    2. A kaggle.json file at ~/.kaggle/kaggle.json (Linux/Mac) or
       C:\\Users\\<you>\\.kaggle\\kaggle.json (Windows), containing:
       {"username": "your_username", "key": "your_api_key"}

Usage:
    python kaggle_download.py

Downloads each candidate dataset as a zip into ./kaggle_datasets/<slug>/ and
extracts it. Once done, copy the whole kaggle_datasets/ folder into the
RailLens project (e.g. rail-dataset-analyzer/kaggle_datasets/) and let me
know - I'll inspect the actual columns/coverage and tell you honestly whether
any of it is usable (per-stop distance, newer trains, etc.) before merging
anything in.
"""
import subprocess
import sys
from pathlib import Path

CANDIDATES = [
    "rohan26x/indian-express-train-dataset",
    "dhanashrishirsath/railyatri-railway-schedule-dataset",
    "dnyaneshyeole/indian-trains",
    "bhavyarajdev/indian-railways-schedule-prices-availability-data",
    "harsh16/indian-railways-time-table-for-trains-available",
    "flugeltomar/indian-railway-dataset",
]

OUT_DIR = Path(__file__).resolve().parent / "kaggle_datasets"
OUT_DIR.mkdir(exist_ok=True)


def main():
    for slug in CANDIDATES:
        name = slug.split("/")[-1]
        dest = OUT_DIR / name
        dest.mkdir(exist_ok=True)
        print(f"\n=== Downloading {slug} ===")
        result = subprocess.run(
            [sys.executable, "-m", "kaggle", "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"],
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"FAILED: {slug}")
            print(result.stderr)
        else:
            print(f"OK: {slug} -> {dest}")

    print("\nDone. Now copy the kaggle_datasets/ folder into the RailLens project folder.")


if __name__ == "__main__":
    main()
