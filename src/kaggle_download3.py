"""
Round 3 of Kaggle dataset downloads for RailLens - run this LOCALLY, same as
kaggle_download.py / kaggle_download2.py (the sandbox this assistant runs in
still can't reach kaggle.com - confirmed again on 2026-07-30: outbound
requests get a 403 from the sandbox's proxy).

Setup / auth: same as kaggle_download.py (pip install kaggle, kaggle.json in
~/.kaggle/ or KAGGLE_USERNAME/KAGGLE_KEY env vars).

Usage:
    python kaggle_download3.py

Downloads into ./kaggle_datasets3/<slug>/ next to this script. Once done,
copy kaggle_datasets3/ into the RailLens project (e.g.
rail-dataset-analyzer/kaggle_datasets3/) and let me know - I'll check each
one against datasets/data_needed.csv (currently 31,822 missing stop-rows /
2,566 trains, 100% missing per-stop Distance) and fold in anything real.

Why this list is short: a fresh Kaggle search on 2026-07-30 for Indian
Railways train/schedule datasets turned up almost the exact same set already
tried in kaggle_download.py and kaggle_download2.py. No genuinely new
dataset surfaced. The one item below is worth a repeat pull, not a first
pull.
"""
import subprocess
import sys
from pathlib import Path

CANDIDATES = [
    # Same slug as round 1 (rohan26x/indian-express-train-dataset), but its
    # Kaggle listing now shows "updated September 2025" - worth re-pulling
    # in case the copy used for the original merge predates that update and
    # picked up newer trains/stops/distance values since.
    "rohan26x/indian-express-train-dataset",
]

OUT_DIR = Path(__file__).resolve().parent / "kaggle_datasets3"
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

    print("\nDone. Copy kaggle_datasets3/ into the RailLens project folder.")


if __name__ == "__main__":
    main()
