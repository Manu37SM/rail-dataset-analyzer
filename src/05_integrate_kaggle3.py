#!/usr/bin/env python3
"""
05_integrate_kaggle3.py
========================
Integrates the round-3 Kaggle source (kaggle_datasets3/indian-express-train-dataset,
slug rohan26x/indian-express-train-dataset, EXP/PASS/SF-TRAINS.json) into
datasets/railway_dataset_ultimate.csv, targeting the gap tracked in
datasets/data_needed.csv (trains present in the ultimate dataset with an
incomplete stop sequence).

WHY A CONFIDENCE FILTER, NOT A BLANKET MERGE:
  Matching purely on Train No is not enough to trust a route swap - Indian
  Railways train numbers get reused/renumbered over the years, and
  data_needed.csv's own per-stop Station Code/Name fields are known to be
  corrupted for a chunk of rows (single-letter truncated codes, see
  README_CLEANANDMERGE.md section 3.2), so per-stop name/code comparison
  isn't reliable either.

  Instead, for every Train No that appears in both data_needed.csv and the
  new source, this script fuzzy-compares (rapidfuzz, same library the
  project already uses in station_resolver.py) the ultimate dataset's
  per-train Source Station Name / Destination Station Name against the new
  source's first/last stop name. A train is only integrated if BOTH ends
  score >= FUZZY_THRESHOLD - this survives real station renames (e.g.
  "Trivandrum" -> "Thiruvananthapuram", "Bangalore City" -> "KSR
  Bengaluru") while rejecting genuine mismatches. Trains that fail this
  check are left untouched in both files - NOT guessed - so they remain
  visible in data_needed.csv for a future, better-matched source.

WHAT "INTEGRATE" MEANS FOR A MATCHED TRAIN:
  All of that Train No's existing rows (its incomplete fragment) are
  DROPPED from the ultimate dataset and replaced with the new source's full
  stop sequence (SEQ, Station Code, Station Name, Arrival time, Departure
  Time, Distance, Source/Destination Station + name). This is a full-
  sequence swap, not a row splice, for the same reason 04_fill_and_merge.py
  never splices two sources' stop lists: there's no reliable way to
  interleave two independently-captured route captures without risking a
  fabricated stop order. The new source's sequence is complete (has
  Distance on every row) where the old fragment was not, so this is a
  strict improvement whenever a train is matched.

  Values transformed from the source JSON on the way in:
    - "H:MM"/"HH:MM"                -> "HH:MM:SS" (zero-padded, +":00")
    - "Source" (first stop arrival) -> "" (blank, matches existing convention)
    - "Destination" (last stop dep) -> "" (blank, matches existing convention)
    - "NN kms"                      -> "NN" (int, matches existing convention)
    - "STATION NAME - CODE"         -> split into Station Name / Station Code

  No provenance column is added to the CSV - datasets/railway_dataset_ultimate.csv
  keeps its original 12-column schema exactly. Traceability for this batch
  lives here and in the changelog JSON instead (unlike the round-1/2 merge,
  which did add "Source Dataset"/"Timing Source" columns to its own output -
  this dataset's schema is being kept clean per explicit instruction).

OUTPUTS:
  datasets/railway_dataset_ultimate.csv   (rewritten)
  datasets/data_needed.csv                (rewritten, resolved trains removed)
  rail-dataset-analyzer/output/kaggle3_integration_changelog.json
"""
import csv
import json
import re
import sys
from pathlib import Path
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = ROOT / "datasets"
KAGGLE_DIR = ROOT / "rail-dataset-analyzer" / "kaggle_datasets3" / "indian-express-train-dataset"
OUTPUT_DIR = ROOT / "rail-dataset-analyzer" / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

ULTIMATE_PATH = DATASETS_DIR / "railway_dataset_ultimate.csv"
NEEDED_PATH = DATASETS_DIR / "data_needed.csv"
CHANGELOG_PATH = OUTPUT_DIR / "kaggle3_integration_changelog.json"

FUZZY_THRESHOLD = 70
SOURCE_TAG = "kaggle_round3"

BASE_COLS = ["Train No", "Train Name", "SEQ", "Station Code", "Station Name",
             "Arrival time", "Departure Time", "Distance", "Source Station",
             "Source Station Name", "Destination Station", "Destination Station Name"]

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
DIST_RE = re.compile(r"^(\d+)\s*kms?$", re.I)


def norm_name(s):
    s = s.upper()
    s = re.sub(r"\bJN\b|\bJUNCTION\b|\bCITY\b|\bCENTRAL\b|\bCNTL\b|\bTOWN\b|\bTERMINUS\b|\bTERM\b", "", s)
    s = re.sub(r"[^A-Z]", "", s)
    return s


def norm_time(v):
    m = TIME_RE.match(v.strip())
    if not m:
        return ""
    h, mi = m.groups()
    return f"{int(h):02d}:{mi}:00"


def parse_distance(v):
    m = DIST_RE.match(v.strip())
    return m.group(1) if m else ""


def split_station(s):
    name, _, code = s.rpartition(" - ")
    return name.strip(), code.strip()


def load_kaggle_trains():
    trains = {}
    dupes = []
    for fn in ["EXP-TRAINS.json", "PASS-TRAINS.json", "SF-TRAINS.json"]:
        with open(KAGGLE_DIR / fn) as fh:
            data = json.load(fh)
        for t in data:
            num = str(int(t["trainNumber"]))
            if num in trains:
                dupes.append(num)
            trains[num] = t
    return trains, dupes


def load_needed_meta_and_rows():
    """Return (per-train meta for matching, all rows grouped by Train No)."""
    meta = {}
    rows_by_train = {}
    with open(NEEDED_PATH, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            tn = row["Train No"].strip().lstrip("0") or "0"
            rows_by_train.setdefault(tn, []).append(row)
            if tn not in meta:
                meta[tn] = (norm_name(row["Source Station Name"]), norm_name(row["Destination Station Name"]))
    return meta, rows_by_train


def build_new_rows(tn, train_name, route):
    """Build BASE_COLS rows for one train from its kaggle route."""
    if not route:
        return []
    src_name, src_code = split_station(route[0]["stationName"])
    dst_name, dst_code = split_station(route[-1]["stationName"])
    out = []
    for stop in route:
        st_name, st_code = split_station(stop["stationName"])
        arr = "" if stop.get("arrives") == "Source" else norm_time(stop.get("arrives", ""))
        dep = "" if stop.get("departs") == "Destination" else norm_time(stop.get("departs", ""))
        dist = parse_distance(stop.get("distance", ""))
        out.append({
            "Train No": tn,
            "Train Name": train_name,
            "SEQ": stop.get("sno", ""),
            "Station Code": st_code,
            "Station Name": st_name,
            "Arrival time": arr,
            "Departure Time": dep,
            "Distance": dist,
            "Source Station": src_code,
            "Source Station Name": src_name,
            "Destination Station": dst_code,
            "Destination Station Name": dst_name,
        })
    return out


def main():
    kaggle_trains, dupes = load_kaggle_trains()
    needed_meta, needed_rows_by_train = load_needed_meta_and_rows()

    overlap = set(needed_meta) & set(kaggle_trains)

    matched = []
    rejected = []
    for tn in overlap:
        src_n, dst_n = needed_meta[tn]
        route = kaggle_trains[tn]["trainRoute"]
        if not route:
            rejected.append({"train_no": tn, "reason": "empty_route_in_source"})
            continue
        k_src_name, _ = split_station(route[0]["stationName"])
        k_dst_name, _ = split_station(route[-1]["stationName"])
        src_score = fuzz.ratio(src_n, norm_name(k_src_name)) if src_n else 0
        dst_score = fuzz.ratio(dst_n, norm_name(k_dst_name)) if dst_n else 0
        if src_score >= FUZZY_THRESHOLD and dst_score >= FUZZY_THRESHOLD:
            matched.append(tn)
        else:
            rejected.append({"train_no": tn, "reason": "endpoint_mismatch",
                              "src_score": round(src_score, 1), "dst_score": round(dst_score, 1)})

    matched_set = set(matched)

    # ---- Build replacement rows for matched trains ----
    # NOTE: no "Source Dataset" (or any other) tracking column is added here -
    # datasets/railway_dataset_ultimate.csv's schema is exactly BASE_COLS and
    # stays that way. Provenance for this batch lives in this script + the
    # changelog JSON, not in the CSV itself.
    replacement_rows = []
    for tn in matched:
        t = kaggle_trains[tn]
        rows = build_new_rows(tn, t["trainName"], t["trainRoute"])
        replacement_rows.extend(rows)

    # ---- Stream-rewrite the ultimate dataset: drop matched trains' old rows, append new ones ----
    tmp_ultimate = OUTPUT_DIR / "railway_dataset_ultimate.tmp.csv"
    dropped_old_rows = 0
    total_old_rows = 0
    with open(ULTIMATE_PATH, newline="") as fin, open(tmp_ultimate, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        fieldnames = BASE_COLS
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            total_old_rows += 1
            tn = row["Train No"].strip()
            if tn.lstrip("0") in matched_set or tn in matched_set:
                dropped_old_rows += 1
                continue
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        for row in replacement_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    tmp_ultimate.replace(ULTIMATE_PATH)

    # ---- Rewrite data_needed.csv: drop rows for matched (now-resolved) trains ----
    tmp_needed = OUTPUT_DIR / "data_needed.tmp.csv"
    kept_needed_rows = 0
    dropped_needed_rows = 0
    with open(NEEDED_PATH, newline="") as fin, open(tmp_needed, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            tn = row["Train No"].strip().lstrip("0") or "0"
            if tn in matched_set:
                dropped_needed_rows += 1
                continue
            writer.writerow(row)
            kept_needed_rows += 1
    tmp_needed.replace(NEEDED_PATH)

    changelog = {
        "source": "kaggle round 3 - rohan26x/indian-express-train-dataset",
        "kaggle_unique_trains": len(kaggle_trains),
        "kaggle_duplicate_train_numbers_across_files": dupes,
        "data_needed_unique_trains_before": len(needed_meta),
        "overlap_trains_by_number": len(overlap),
        "matched_trains_integrated": len(matched),
        "rejected_trains_endpoint_mismatch_or_empty": len(rejected),
        "fuzzy_threshold_used": FUZZY_THRESHOLD,
        "ultimate_rows_before": total_old_rows,
        "ultimate_rows_dropped_old_fragments": dropped_old_rows,
        "ultimate_rows_added_new": len(replacement_rows),
        "ultimate_rows_after": total_old_rows - dropped_old_rows + len(replacement_rows),
        "data_needed_rows_before": kept_needed_rows + dropped_needed_rows,
        "data_needed_rows_dropped_resolved": dropped_needed_rows,
        "data_needed_rows_after": kept_needed_rows,
        "rejected_sample": rejected[:30],
        "note": "Only trains whose Source/Destination station names fuzzy-matched (rapidfuzz "
                "ratio >= 70) at both ends between data_needed.csv and the new source were "
                "integrated. This is deliberately conservative: per-stop station codes/names in "
                "data_needed.csv are known-corrupted for a subset of rows (truncated single-letter "
                "codes), so per-stop comparison was not used as the trust signal. Rejected trains "
                "are left untouched in data_needed.csv for future sourcing.",
    }
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(changelog, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in changelog.items() if k != "rejected_sample"}, indent=2, default=str))


if __name__ == "__main__":
    main()
