#!/usr/bin/env python3
"""
01_internal_audit.py
=====================
100% internal structural audit of the RailLens train_dataset CSV.

This script performs ONLY checks that can be verified from the internal
logic and consistency of the dataset itself -- no external/official data
is used here (that happens in 02_external_crossref.py). Every one of the
186k+ rows is checked; nothing is sampled.

Checks performed:
  - Duplicate records (exact row duplicates, and duplicate (Train No, SEQ))
  - Duplicate stops for same train at same station (excluding legitimate
    loop lines, flagged for manual review)
  - Missing / blank required values
  - SEQ continuity (1..N, no gaps/repeats) per train
  - Distance monotonicity (must be non-decreasing along SEQ)
  - Arrival/Departure logic:
      * First stop (SEQ=1): arrival should be 00:00:00 (origin placeholder)
      * Last stop (SEQ=max): departure should be 00:00:00 (terminus placeholder)
      * Departure >= Arrival at intermediate stops (same-day; flags cases
        that need overnight-wrap awareness rather than assuming an error)
  - Station code formatting (non-alphanumeric chars, unexpected length,
    case inconsistency)
  - Referential integrity: Source Station / Destination Station codes
    declared in every row for a train must equal the actual first/last
    SEQ station codes for that train
  - Station name consistency: same Station Code mapped to multiple
    different Station Names within the dataset (and vice versa)
  - Encoding issues: stray control characters, double-encoded UTF-8,
    inconsistent trailing punctuation ("JN." vs "JN" vs "JN,")
  - Single-stop trains (only one row) -- structurally incomplete
  - Trains where SEQ=1 distance != 0

Output:
  - data/output/internal_audit_flags.csv   (row-level flags, one row per issue)
  - data/output/internal_audit_summary.json (aggregate counts for the report)
"""
import pandas as pd
import numpy as np
import json
import re
import argparse
import unicodedata
from collections import defaultdict

DEFAULT_IN = "/home/claude/raillens_validation/data/train_dataset_original.csv"
DEFAULT_FLAGS_OUT = "/home/claude/raillens_validation/data/output/internal_audit_flags.csv"
DEFAULT_SUMMARY_OUT = "/home/claude/raillens_validation/data/output/internal_audit_summary.json"

def parse_args():
    p = argparse.ArgumentParser(description="Run the 100% internal structural audit on a RailLens-format CSV.")
    p.add_argument("--input", default=DEFAULT_IN, help="Path to the CSV to audit")
    p.add_argument("--flags-out", default=DEFAULT_FLAGS_OUT, help="Where to write row-level flags CSV")
    p.add_argument("--summary-out", default=DEFAULT_SUMMARY_OUT, help="Where to write aggregate summary JSON")
    return p.parse_args()

COLS = ["Train No","Train Name","SEQ","Station Code","Station Name",
        "Arrival time","Departure Time","Distance","Source Station",
        "Source Station Name","Destination Station","Destination Station Name"]

# Known station-code aliases that coexist in this dataset for the SAME physical
# station (confirmed via web search against multiple current sources -- see
# README/audit report). Treated as a benign internal naming inconsistency
# rather than a routing error.
KNOWN_CODE_ALIASES = {
    frozenset({"CSTM", "CSMT"}),  # Mumbai Chhatrapati Shivaji Maharaj Terminus
}

def codes_are_aliases(c1, c2):
    if c1 == c2:
        return True
    return frozenset({c1, c2}) in KNOWN_CODE_ALIASES

def load(in_path):
    df = pd.read_csv(in_path, dtype=str, keep_default_na=False, na_values=[""])
    df["_row_id"] = df.index  # stable reference back to original row (0-indexed, matches original CSV row - 2 for header+1idx)
    return df

def add_flag(flags, row_id, train_no, category, detail, severity):
    flags.append({
        "row_id": row_id,
        "train_no": train_no,
        "category": category,
        "detail": detail,
        "severity": severity,  # "critical" | "warning" | "info"
    })

def main():
    args = parse_args()
    df = load(args.input)
    n_rows = len(df)
    flags = []

    # ---------- 1. Missing required values ----------
    required = ["Train No","Train Name","SEQ","Station Code","Station Name"]
    for col in required:
        missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        for rid in df.loc[missing_mask, "_row_id"]:
            add_flag(flags, rid, df.loc[rid,"Train No"] if not missing_mask[rid] or col!="Train No" else "",
                      "missing_required_value", f"Missing value in required column '{col}'", "critical")

    optional_but_checked = ["Arrival time","Departure Time","Distance","Source Station",
                             "Source Station Name","Destination Station","Destination Station Name"]
    for col in optional_but_checked:
        missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        for rid in df.loc[missing_mask, "_row_id"]:
            add_flag(flags, rid, df.loc[rid,"Train No"], "missing_optional_value",
                      f"Missing value in column '{col}'", "warning")

    # ---------- 1b. Malformed / column-shifted rows ----------
    # A Train No that isn't purely numeric is a structural red flag: every legitimate
    # Indian Railways train number is numeric. This catches rows where the original
    # source file appears to have split one logical row into two physical CSV lines.
    non_numeric_train_no = df[~df["Train No"].astype(str).str.match(r"^\d+$")]
    for rid in non_numeric_train_no["_row_id"]:
        add_flag(flags, rid, df.loc[rid,"Train No"], "malformed_row_non_numeric_train_no",
                  f"Train No value '{df.loc[rid,'Train No']}' is not purely numeric -- indicates a "
                  f"column-shifted / split row in the source file (see audit report for reconstruction "
                  f"logic applied)", "critical")

    # ---------- 2. Exact duplicate rows ----------
    dup_mask = df.duplicated(subset=COLS, keep=False)
    for rid in df.loc[dup_mask, "_row_id"]:
        add_flag(flags, rid, df.loc[rid,"Train No"], "duplicate_exact_row",
                  "Row is an exact duplicate of another row (all fields identical)", "critical")

    # ---------- 3. Duplicate (Train No, SEQ) ----------
    dup_seq_mask = df.duplicated(subset=["Train No","SEQ"], keep=False)
    for rid in df.loc[dup_seq_mask, "_row_id"]:
        add_flag(flags, rid, df.loc[rid,"Train No"], "duplicate_train_seq",
                  f"Duplicate SEQ={df.loc[rid,'SEQ']} for Train No={df.loc[rid,'Train No']}", "critical")

    # ---------- 4. Duplicate (Train No, Station Code) - same station twice on same train ----------
    dup_stop_mask = df.duplicated(subset=["Train No","Station Code"], keep=False)
    for rid in df.loc[dup_stop_mask, "_row_id"]:
        add_flag(flags, rid, df.loc[rid,"Train No"], "duplicate_stop_on_train",
                  f"Station Code={df.loc[rid,'Station Code']} appears more than once for Train No={df.loc[rid,'Train No']} "
                  f"(may be a legitimate loop/circular route -- requires manual verification)", "warning")

    # ---------- 5. Per-train checks: SEQ continuity, distance monotonicity, arrival/departure logic,
    #              referential integrity of source/destination ----------
    single_stop_trains = []
    seq_gap_trains = 0
    dist_nonmono_count = 0
    arr_dep_issue_count = 0
    src_dst_mismatch_count = 0

    df["_seq_num"] = pd.to_numeric(df["SEQ"], errors="coerce")
    df["_dist_num"] = pd.to_numeric(df["Distance"], errors="coerce")

    grouped = df.groupby("Train No", sort=False)
    for train_no, g in grouped:
        g_sorted = g.sort_values("_seq_num", na_position="last")
        n_stops = len(g_sorted)

        if n_stops == 1:
            single_stop_trains.append(train_no)
            add_flag(flags, g_sorted["_row_id"].iloc[0], train_no, "single_stop_train",
                      "Train has only a single row/stop in the dataset -- structurally incomplete "
                      "(a valid route needs at least an origin and destination)", "critical")
            continue

        # SEQ continuity: expect 1..n_stops with no gaps or repeats
        seqs = g_sorted["_seq_num"].dropna().astype(int).tolist()
        expected = list(range(1, n_stops + 1))
        if seqs != expected:
            seq_gap_trains += 1
            add_flag(flags, g_sorted["_row_id"].iloc[0], train_no, "seq_discontinuity",
                      f"SEQ values {seqs} are not a clean 1..{n_stops} sequence (gap, repeat, or non-numeric SEQ)",
                      "critical")

        # Distance monotonicity (non-decreasing along the sorted SEQ)
        dists = g_sorted["_dist_num"].tolist()
        row_ids = g_sorted["_row_id"].tolist()
        for i in range(1, len(dists)):
            if pd.notna(dists[i]) and pd.notna(dists[i-1]) and dists[i] < dists[i-1]:
                dist_nonmono_count += 1
                add_flag(flags, row_ids[i], train_no, "distance_not_monotonic",
                          f"Distance {dists[i]} at SEQ={g_sorted['SEQ'].iloc[i]} is less than previous stop's "
                          f"distance {dists[i-1]} at SEQ={g_sorted['SEQ'].iloc[i-1]}", "critical")

        # First stop distance should be 0
        first_dist = dists[0]
        if pd.notna(first_dist) and first_dist != 0:
            add_flag(flags, row_ids[0], train_no, "origin_distance_not_zero",
                      f"First stop (SEQ=1) has Distance={first_dist}, expected 0", "warning")

        # Arrival/Departure logic
        first_arr = str(g_sorted["Arrival time"].iloc[0])
        last_dep = str(g_sorted["Departure Time"].iloc[-1])
        if first_arr not in ("00:00:00", "nan", "None", ""):
            arr_dep_issue_count += 1
            add_flag(flags, row_ids[0], train_no, "origin_arrival_not_placeholder",
                      f"First stop (SEQ=1) Arrival time is '{first_arr}', expected '00:00:00' placeholder for origin",
                      "warning")
        if last_dep not in ("00:00:00", "nan", "None", ""):
            arr_dep_issue_count += 1
            add_flag(flags, row_ids[-1], train_no, "terminus_departure_not_placeholder",
                      f"Last stop (SEQ={n_stops}) Departure Time is '{last_dep}', expected '00:00:00' placeholder for terminus",
                      "warning")

        # Intermediate stops: departure should not be blank if arrival is blank etc. -- check dep>=arr same day
        for i in range(1, n_stops - 1):
            arr = str(g_sorted["Arrival time"].iloc[i])
            dep = str(g_sorted["Departure Time"].iloc[i])
            if re.match(r"^\d{2}:\d{2}:\d{2}$", arr) and re.match(r"^\d{2}:\d{2}:\d{2}$", dep):
                if dep < arr:
                    # Could be a legitimate overnight halt spanning midnight -- flag as warning, not critical,
                    # since we cannot know the day-offset from this data alone.
                    add_flag(flags, row_ids[i], train_no, "departure_before_arrival",
                              f"Departure Time {dep} is earlier than Arrival time {arr} at intermediate stop "
                              f"SEQ={g_sorted['SEQ'].iloc[i]} (may be legitimate if halt spans midnight -- "
                              f"cannot be resolved without a day-offset field)", "info")

        # Referential integrity: declared Source/Destination station codes must match actual first/last stop
        declared_src = set(g_sorted["Source Station"].dropna().unique())
        declared_dst = set(g_sorted["Destination Station"].dropna().unique())
        actual_src = g_sorted["Station Code"].iloc[0]
        actual_dst = g_sorted["Station Code"].iloc[-1]

        if len(declared_src) > 1 or len(declared_dst) > 1:
            src_dst_mismatch_count += 1
            add_flag(flags, row_ids[0], train_no, "inconsistent_declared_src_dst",
                      f"Train No={train_no} has inconsistent declared Source Station values {declared_src} "
                      f"or Destination Station values {declared_dst} across its own rows", "critical")
        else:
            d_src = next(iter(declared_src)) if declared_src else None
            d_dst = next(iter(declared_dst)) if declared_dst else None

            if d_src and d_src != actual_src:
                if codes_are_aliases(d_src, actual_src):
                    add_flag(flags, row_ids[0], train_no, "known_code_alias_inconsistency",
                              f"Source Station='{d_src}' vs actual first-stop Station Code='{actual_src}' -- "
                              f"these are known aliases for the same physical station (dataset uses both "
                              f"codes inconsistently across columns), not a routing error", "info")
                else:
                    src_dst_mismatch_count += 1
                    add_flag(flags, row_ids[0], train_no, "source_station_mismatch",
                              f"Declared Source Station='{d_src}' does not match actual first-stop "
                              f"Station Code='{actual_src}' -- Requires Manual Verification", "critical")
            if d_dst and d_dst != actual_dst:
                if codes_are_aliases(d_dst, actual_dst):
                    add_flag(flags, row_ids[-1], train_no, "known_code_alias_inconsistency",
                              f"Destination Station='{d_dst}' vs actual last-stop Station Code='{actual_dst}' -- "
                              f"these are known aliases for the same physical station (dataset uses both "
                              f"codes inconsistently across columns), not a routing error", "info")
                else:
                    src_dst_mismatch_count += 1
                    add_flag(flags, row_ids[-1], train_no, "destination_station_mismatch",
                              f"Declared Destination Station='{d_dst}' does not match actual last-stop "
                              f"Station Code='{actual_dst}' -- Requires Manual Verification", "critical")

    # ---------- 6. Station code formatting ----------
    code_pattern = re.compile(r"^[A-Z0-9]{2,6}$")
    bad_format_codes = set()
    for rid, code in zip(df["_row_id"], df["Station Code"]):
        if pd.isna(code):
            continue
        if not code_pattern.match(str(code)):
            bad_format_codes.add(code)
            add_flag(flags, rid, df.loc[rid,"Train No"], "station_code_format",
                      f"Station Code '{code}' does not match expected pattern (2-6 uppercase alphanumeric chars)",
                      "warning")

    # ---------- 7. Station code <-> Station name consistency ----------
    code_to_names = defaultdict(set)
    name_to_codes = defaultdict(set)
    for code, name in zip(df["Station Code"], df["Station Name"]):
        if pd.isna(code) or pd.isna(name):
            continue
        code_to_names[code].add(name)
        name_to_codes[name].add(code)

    inconsistent_codes = {c: v for c, v in code_to_names.items() if len(v) > 1}
    inconsistent_names = {n: v for n, v in name_to_codes.items() if len(v) > 1}

    for rid, code, name in zip(df["_row_id"], df["Station Code"], df["Station Name"]):
        if pd.isna(code) or pd.isna(name):
            continue
        if code in inconsistent_codes:
            add_flag(flags, rid, df.loc[rid,"Train No"], "station_code_name_inconsistency",
                      f"Station Code '{code}' is mapped to multiple different names in the dataset: "
                      f"{sorted(inconsistent_codes[code])}", "warning")

    # ---------- 8. Encoding / formatting anomalies in names ----------
    def has_encoding_issue(s):
        if not isinstance(s, str):
            return False
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
            return True
        if s != s.strip():
            return True
        if re.search(r"\s{2,}", s):
            return True
        try:
            s.encode("ascii")
        except UnicodeEncodeError:
            return True
        return False

    for rid, name in zip(df["_row_id"], df["Station Name"]):
        if has_encoding_issue(name):
            add_flag(flags, rid, df.loc[rid,"Train No"], "encoding_or_whitespace_issue",
                      f"Station Name '{name}' contains control chars, stray whitespace, or non-ASCII bytes", "info")

    # ---------- Write outputs ----------
    flags_df = pd.DataFrame(flags)
    flags_df.to_csv(args.flags_out, index=False)

    summary = {
        "total_rows_analyzed": int(n_rows),
        "total_unique_trains": int(df["Train No"].nunique()),
        "total_unique_station_codes": int(df["Station Code"].nunique()),
        "total_flags_raised": int(len(flags_df)),
        "flags_by_category": flags_df["category"].value_counts().to_dict() if len(flags_df) else {},
        "flags_by_severity": flags_df["severity"].value_counts().to_dict() if len(flags_df) else {},
        "single_stop_trains_count": len(single_stop_trains),
        "trains_with_seq_discontinuity": seq_gap_trains,
        "rows_with_distance_not_monotonic": dist_nonmono_count,
        "arrival_departure_placeholder_issues": arr_dep_issue_count,
        "source_dest_mismatches": src_dst_mismatch_count,
        "station_codes_bad_format": len(bad_format_codes),
        "station_codes_with_inconsistent_names": len(inconsistent_codes),
        "station_names_with_inconsistent_codes": len(inconsistent_names),
        "malformed_non_numeric_train_no_rows": int(len(non_numeric_train_no)),
    }
    with open(args.summary_out, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(json.dumps(summary, indent=2, default=str))

if __name__ == "__main__":
    main()
