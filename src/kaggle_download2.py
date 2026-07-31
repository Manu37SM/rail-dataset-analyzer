"""
Round 2 of Kaggle dataset downloads for RailLens - run this LOCALLY, same as
before (pip install kaggle, kaggle.json already set up from last time).

Usage:
    python kaggle_download2.py

Downloads into ./kaggle_datasets2/<slug>/ next to this script. Once done,
copy the kaggle_datasets2/ folder into the RailLens project (e.g.
rail-dataset-analyzer/kaggle_datasets2/) and tell me it's there - I'll check
each one against the current data_needed.csv gap and fold in anything real,
then delete the raw dumps again once done (keeping just the two final files).
"""
import subprocess
import sys
from pathlib import Path

CANDIDATES = [
    # Name suggests the most recently updated general train dataset found in
    # this search round - unverified contents until downloaded.
    "arihantjain09/indian-railways-latest",

    # Station master list with lat/lon - could help corroborate ambiguous
    # station codes geographically (not schedule/distance data itself).
    "rishabhbhartiya/indian-railway-all-indian-railway-station-dataset",

    # Train delay records - unlikely to have per-stop distance, but may carry
    # arrival/departure times worth checking against the remaining gap.
    "vishwassrivastava1/indian-railway-delay-dataset",

    # General train info dump (2019 vintage per Kaggle listing) - low
    # priority, included for completeness since it turned up in the search.
    "binilj04/irctctraininfo",

    # "Data on one of the largest railway systems in the world" - general
    # dataset, contents unverified, seen in earlier search rounds too.
    "sripaadsrinivasan/indian-railways-dataset",

    # Special/festival trains 2020-2021 - narrow scope (COVID-era special
    # trains only) but included since it turned up in search.
    "noobidoobidoo/india-special-trains-dataset-2020-2021",

    # "Indian Railways Passenger Train Delays Dataset 2025" - newest delay
    # dataset found, may carry recent arrival/departure times.
    "naijilaji/indian-railways-passenger-train-delays-dataset",

    # General Indian trains CSV, contents/vintage unverified.
    "ravibhalala217/indiantrains",

    # "All trains run by IRCTC as given by cleartrip" per listing - general
    # train list, contents unverified.
    "akashm103/irctc-trains",

    # Explicitly named "tiny" by its author - low expectations, included for
    # completeness.
    "railwayreservation/indianrailwayreservationtinydataset",
]

# Skipped as clearly not applicable: shaurcastic's "Indian Railway Dataset
# (Object Detection)" is an image dataset for computer vision, not tabular
# schedule data; niknmarjan's "RapidKL Train Dataset" is Malaysian light
# rail, not Indian Railways.

OUT_DIR = Path(__file__).resolve().parent / "kaggle_datasets2"
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

    print("\nDone. Copy kaggle_datasets2/ into the RailLens project folder.")


if __name__ == "__main__":
    main()