#!/usr/bin/env python3
"""
03_apply_fixes.py
==================
Applies ONLY the fixes that meet a high-confidence, fully-documented,
non-destructive bar. Nothing in this script "guesses" -- every change is
either (a) a mechanical reconstruction using data already present elsewhere
in the same file, or (b) a clearly-labeled additive enrichment column sourced
from a bulk reference dataset, with the original columns left untouched.

Fixes applied (all row-level, fully traceable):
  1. Reconstruct the 5 "split row" corruptions (Train No == a stray
     non-numeric fragment, e.g. "K"). Confirmed pattern: the original source
     file split one logical row into two physical CSV lines around the
     KALGURKI H (KGIH) stop on trains 6919, 6920, 56905, 56906, 57641. In
     every case, the row immediately BEFORE the malformed row has the
     correct Train No/Train Name/SEQ/Station Code/Station Name but "NA"
     placeholders for the remaining 7 fields, and the malformed row supplies
     exactly those 7 missing fields (shifted left by one column, with a
     stray leading token replacing what should have been nothing). This is
     reconstructed by concatenation, not inference -- every value used
     already exists verbatim in the source file.
  2. Add two NEW, additive columns (originals untouched):
       - "Station Name (Community Reference)": the full station name from
         the datameet/railways bulk reference, populated ONLY where the
         dataset's Station Name is exactly the reference name truncated to
         12 characters (see 02_external_crossref.py TRUNCATION_LEN logic) --
         i.e. only where we are highly confident it is the SAME name, just
         cut off by the source system's 12-character field limit.
       - "Validation Status": machine-readable rollup per row (VERIFIED /
         VERIFIED_TRUNCATED_IN_SOURCE / REQUIRES_MANUAL_VERIFICATION / etc.)
         for the Station Code, joined from the crossref output, so a human
         reviewer can filter instantly.

Everything else identified by 01_internal_audit.py and 02_external_crossref.py
(name mismatches, trains not found in the reference, CSTM/CSMT alias
inconsistency, source/destination mismatches on trains 7062 & 8064, etc.) is
LEFT EXACTLY AS-IS in the data, and is only recorded in the audit report as
"Requires Manual Verification". No value is invented or altered based on a
guess.
"""
import pandas as pd
import json

IN_PATH = "/home/claude/raillens_validation/data/train_dataset_original.csv"
STATION_CROSSREF = "/home/claude/raillens_validation/data/output/station_crossref.csv"
OUT_PATH = "/home/claude/raillens_validation/data/output/train_dataset_cleaned.csv"
CHANGELOG_OUT = "/home/claude/raillens_validation/data/output/cleaning_changelog.json"

COLS = ["Train No","Train Name","SEQ","Station Code","Station Name",
        "Arrival time","Departure Time","Distance","Source Station",
        "Source Station Name","Destination Station","Destination Station Name"]


def main():
    df = pd.read_csv(IN_PATH, dtype=str, keep_default_na=False, na_values=[""])
    df = df.reset_index(drop=True)
    changelog = []

    # ---------------- FIX 1: reconstruct split "K"-corrupted rows ----------------
    # Find malformed rows (non-numeric Train No)
    malformed_idx = df.index[~df["Train No"].astype(str).str.match(r"^\d+$")].tolist()
    rows_to_drop = []
    for mi in malformed_idx:
        prev_i = mi - 1
        if prev_i < 0:
            continue  # can't reconstruct without a preceding row; leave as-is
        prev = df.loc[prev_i]
        bad = df.loc[mi]

        # Sanity check the expected corruption pattern before touching anything:
        # the previous row must have NA placeholders in the last 7 columns.
        prev_tail = [prev["Arrival time"], prev["Departure Time"], prev["Distance"],
                     prev["Source Station"], prev["Source Station Name"],
                     prev["Destination Station"], prev["Destination Station Name"]]
        if not all(str(v).strip().upper() in ("NA", "NAN", "") or pd.isna(v) for v in prev_tail):
            continue  # doesn't match the known pattern -- do not touch, leave flagged

        # The malformed row's own fields, read positionally, are:
        # [TrainNo(garbage), TrainName-slot=Arrival, SEQ-slot=Departure, StationCode-slot=Distance,
        #  StationName-slot=SourceStation, Arrival-slot=SourceStationName, Departure-slot=DestStation,
        #  Distance-slot=DestStationName, ...trailing NA...]
        bad_vals = bad[COLS].tolist()
        reconstructed_tail = bad_vals[1:8]  # 7 values: Arrival..DestStationName

        if len(reconstructed_tail) != 7:
            continue

        old_row_repr = prev[COLS].tolist()
        for col, val in zip(COLS[5:12], reconstructed_tail):
            df.at[prev_i, col] = val

        rows_to_drop.append(mi)
        changelog.append({
            "action": "reconstructed_split_row",
            "train_no": prev["Train No"],
            "station_code": prev["Station Code"],
            "seq": prev["SEQ"],
            "before": dict(zip(COLS, old_row_repr)),
            "after": dict(zip(COLS, df.loc[prev_i, COLS].tolist())),
            "malformed_row_removed": dict(zip(COLS, bad_vals)),
            "reason": "Source file split one logical row into two physical CSV lines around this "
                      "stop; reconstructed by concatenating the two fragments, both already present "
                      "verbatim in the original file. No values were invented.",
        })

    df = df.drop(index=rows_to_drop).reset_index(drop=True)

    # ---------------- FIX 2: additive enrichment columns (non-destructive) ----------------
    crossref = pd.read_csv(STATION_CROSSREF, dtype=str)
    crossref_map = crossref.set_index("station_code")[["status", "suggested_full_name"]].to_dict("index")

    df["Validation Status"] = df["Station Code"].map(
        lambda c: crossref_map.get(c, {}).get("status", "REQUIRES_MANUAL_VERIFICATION")
    )
    df["Station Name (Community Reference)"] = df.apply(
        lambda r: crossref_map.get(r["Station Code"], {}).get("suggested_full_name")
                  if crossref_map.get(r["Station Code"], {}).get("status") == "VERIFIED_TRUNCATED_IN_SOURCE"
                  else "",
        axis=1
    )

    df.to_csv(OUT_PATH, index=False)

    with open(CHANGELOG_OUT, "w") as f:
        json.dump({
            "rows_reconstructed": len(rows_to_drop),
            "rows_removed_after_reconstruction": len(rows_to_drop),
            "net_row_count_change": len(rows_to_drop) * -1,
            "original_row_count": len(pd.read_csv(IN_PATH, dtype=str)),
            "cleaned_row_count": len(df),
            "changelog_entries": changelog,
            "columns_added": ["Validation Status", "Station Name (Community Reference)"],
            "note": "All original columns are byte-for-byte unchanged except for the 5 rows "
                    "involved in the split-row reconstruction fix. Two new columns were appended "
                    "for transparency; no existing column was altered or removed.",
        }, f, indent=2, default=str)

    print(f"Original rows: {len(pd.read_csv(IN_PATH, dtype=str))}")
    print(f"Cleaned rows:  {len(df)}")
    print(f"Rows reconstructed & malformed duplicates removed: {len(rows_to_drop)}")
    print(f"Changelog entries: {len(changelog)}")


if __name__ == "__main__":
    main()
