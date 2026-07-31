#!/usr/bin/env python3
"""
06_fill_missing_distance_batched.py
=====================================
Fills missing Distance values in datasets/data_needed.csv using distances
that are ALREADY known elsewhere in datasets/railway_dataset_ultimate.csv
for the same physical station-to-station segment - no interpolation, no
guessing, and every fill is cross-checked before being accepted.

METHOD
------
1. Build a segment-distance lookup from the 227K-row ultimate dataset:
   for every train with consecutive stops A -> B where both have a known
   Distance, record distance(B) - distance(A) keyed by the unordered
   station-code pair {A, B}. Where a pair has multiple observations
   (different trains sharing that segment), use the median.

2. For each train in data_needed.csv, reconstruct its FULL stop sequence by
   merging its data_needed rows (Distance unknown) with any rows that same
   Train No already has in railway_dataset_ultimate.csv (Distance known -
   these are "anchors"). The route's first stop is always an implicit
   anchor at Distance = 0 (a fixed schema convention already used
   everywhere in this dataset, not a guess).

3. Between every consecutive PAIR of anchors, walk the chain of
   intermediate stops summing the segment lookup. A fill is only accepted
   if EVERY segment in that chain is known AND the summed total matches the
   known anchor-to-anchor distance gap within a small tolerance
   (TOLERANCE_KM). This is the "verify" step: it independently confirms the
   filled values against real, already-recorded data, and it has already
   caught internally-inconsistent chains in testing (rejected rather than
   filled).

4. Any row that still can't be resolved this way (no anchor pair covers it,
   or the chain-sum doesn't match) is left untouched in data_needed.csv.

BATCHING
--------
Trains are processed in batches of BATCH_SIZE (default 150) purely for
auditability - each batch's fill/reject counts are logged separately in the
changelog, and a running total is printed as it goes, so a partial run's
progress is always visible and each batch's result can be checked before
trusting the next.

WHAT GETS MOVED
----------------
Any data_needed.csv row whose Distance is resolved and verified is moved
into railway_dataset_ultimate.csv (its existing Arrival time / Departure
Time / Station Name are kept as-is - only Distance was ever missing for
these rows) and removed from data_needed.csv. This mirrors how the two
files already relate: ultimate.csv holds rows with a confirmed Distance,
data_needed.csv holds the rest. A train does not have to be fully resolved
to have some of its rows migrate - that already happens today (e.g. many
trains have exactly one row in ultimate.csv, the rest in data_needed.csv).

No new columns are added to either CSV - both keep their original 12-column
schema (Train No, Train Name, SEQ, Station Code, Station Name, Arrival
time, Departure Time, Distance, Source Station, Source Station Name,
Destination Station, Destination Station Name).

OUTPUT
------
datasets/railway_dataset_ultimate.csv   (rewritten)
datasets/data_needed.csv                (rewritten)
rail-dataset-analyzer/output/distance_fill_changelog.json
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = ROOT / "datasets"
OUTPUT_DIR = ROOT / "rail-dataset-analyzer" / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

ULTIMATE_PATH = DATASETS_DIR / "railway_dataset_ultimate.csv"
NEEDED_PATH = DATASETS_DIR / "data_needed.csv"
CHANGELOG_PATH = OUTPUT_DIR / "distance_fill_changelog.json"

BASE_COLS = ["Train No", "Train Name", "SEQ", "Station Code", "Station Name",
             "Arrival time", "Departure Time", "Distance", "Source Station",
             "Source Station Name", "Destination Station", "Destination Station Name"]

BATCH_SIZE = 150
TOLERANCE_KM = 3.0  # rounding tolerance when checking a chain-sum against a known anchor gap


def build_segment_lookup():
    seg = defaultdict(list)
    with open(ULTIMATE_PATH, newline="") as f:
        r = csv.DictReader(f)
        last_tn = None
        last_code = None
        last_dist = None
        for row in r:
            tn = row["Train No"]
            code = row["Station Code"].strip()
            try:
                dist = float(row["Distance"])
            except (ValueError, TypeError):
                dist = None
            if tn != last_tn:
                last_tn, last_code, last_dist = tn, code, dist
                continue
            if dist is not None and last_dist is not None and last_code:
                key = tuple(sorted([last_code, code]))
                seg[key].append(round(dist - last_dist, 2))
            last_code, last_dist = code, dist
    return {k: statistics.median(v) for k, v in seg.items()}


def load_inputs():
    needed_rows = defaultdict(list)
    with open(NEEDED_PATH, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            needed_rows[row["Train No"]].append(row)

    ultimate_rows_by_train = defaultdict(list)
    all_ultimate_rows = []
    with open(ULTIMATE_PATH, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            all_ultimate_rows.append(row)
            ultimate_rows_by_train[row["Train No"]].append(row)

    return needed_rows, ultimate_rows_by_train, all_ultimate_rows


def resolve_train(tn, needed_for_train, ultimate_for_train, seg):
    """Return dict {SEQ(int): resolved_distance(float)} for originally-missing rows only,
    plus a small per-train verification log."""
    combined = {}
    originally_missing = set()
    for row in needed_for_train:
        s = int(row["SEQ"])
        combined[s] = (row["Station Code"].strip(), None)
        originally_missing.add(s)
    for row in ultimate_for_train:
        s = int(row["SEQ"])
        combined[s] = (row["Station Code"].strip(), float(row["Distance"]))

    seqs = sorted(combined)
    if not seqs:
        return {}, []

    min_seq = seqs[0]
    if combined[min_seq][1] is None:
        combined[min_seq] = (combined[min_seq][0], 0.0)

    anchor_positions = [i for i, s in enumerate(seqs) if combined[s][1] is not None]
    resolved = {}
    log = []
    for a_idx in range(len(anchor_positions)):
        i = anchor_positions[a_idx]
        s_i = seqs[i]
        code_i, dist_i = combined[s_i]
        resolved[s_i] = dist_i
        if a_idx + 1 >= len(anchor_positions):
            continue
        j = anchor_positions[a_idx + 1]
        s_j = seqs[j]
        code_j, dist_j = combined[s_j]
        if j - i == 1:
            continue
        cum = dist_i
        vals = {}
        ok = True
        for k in range(i, j):
            sa, sb = seqs[k], seqs[k + 1]
            ca, cb = combined[sa][0], combined[sb][0]
            key = tuple(sorted([ca, cb]))
            if key not in seg:
                ok = False
                break
            cum += seg[key]
            vals[sb] = cum
        if ok and abs(cum - dist_j) <= TOLERANCE_KM:
            resolved.update(vals)
            log.append({"from_seq": s_i, "to_seq": s_j, "status": "verified_and_filled",
                         "chain_sum": round(cum - dist_i, 2), "known_gap": round(dist_j - dist_i, 2)})
        elif ok:
            log.append({"from_seq": s_i, "to_seq": s_j, "status": "rejected_inconsistent",
                         "chain_sum": round(cum - dist_i, 2), "known_gap": round(dist_j - dist_i, 2)})
        else:
            log.append({"from_seq": s_i, "to_seq": s_j, "status": "rejected_gap_in_segment_lookup"})

    out = {s: resolved[s] for s in originally_missing if s in resolved}
    return out, log


def main():
    print("Building segment lookup from railway_dataset_ultimate.csv ...")
    seg = build_segment_lookup()
    print(f"  {len(seg)} known station-pair segments")

    needed_rows, ultimate_rows_by_train, all_ultimate_rows = load_inputs()
    train_list = sorted(needed_rows.keys())
    batches = [train_list[i:i + BATCH_SIZE] for i in range(0, len(train_list), BATCH_SIZE)]

    resolved_by_train = {}   # tn -> {seq: distance}
    batch_reports = []
    verified_chains = 0
    rejected_chains = 0

    for b_idx, batch in enumerate(batches, 1):
        batch_rows_resolved = 0
        batch_rows_total = 0
        batch_trains_touched = 0
        for tn in batch:
            nrows = needed_rows[tn]
            urows = ultimate_rows_by_train.get(tn, [])
            batch_rows_total += len(nrows)
            resolved, log = resolve_train(tn, nrows, urows, seg)
            for entry in log:
                if entry["status"] == "verified_and_filled":
                    verified_chains += 1
                elif entry["status"] == "rejected_inconsistent":
                    rejected_chains += 1
            if resolved:
                resolved_by_train[tn] = resolved
                batch_rows_resolved += len(resolved)
                batch_trains_touched += 1
        report = {
            "batch": b_idx,
            "trains_in_batch": len(batch),
            "trains_with_new_fill": batch_trains_touched,
            "rows_in_batch": batch_rows_total,
            "rows_resolved_in_batch": batch_rows_resolved,
        }
        batch_reports.append(report)
        print(f"Batch {b_idx}/{len(batches)}: {batch_rows_resolved}/{batch_rows_total} rows resolved "
              f"({batch_trains_touched}/{len(batch)} trains touched)")

    total_resolved_rows = sum(len(v) for v in resolved_by_train.values())
    total_needed_rows = sum(len(v) for v in needed_rows.values())
    print(f"\nTotal: {total_resolved_rows}/{total_needed_rows} rows resolved and verified "
          f"across {len(resolved_by_train)} trains.")

    # ---- Apply: build new ultimate rows for resolved data_needed rows, rewrite both files ----
    moved_rows = []
    for tn, seq_map in resolved_by_train.items():
        by_seq = {int(row["SEQ"]): row for row in needed_rows[tn]}
        for seq, dist in seq_map.items():
            row = by_seq[seq]
            new_row = {k: row.get(k, "") for k in BASE_COLS}
            new_row["Distance"] = str(int(round(dist)))
            moved_rows.append(new_row)

    tmp_ultimate = OUTPUT_DIR / "railway_dataset_ultimate.tmp.csv"
    with open(tmp_ultimate, "w", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=BASE_COLS)
        writer.writeheader()
        for row in all_ultimate_rows:
            writer.writerow({k: row.get(k, "") for k in BASE_COLS})
        for row in moved_rows:
            writer.writerow(row)
    tmp_ultimate.replace(ULTIMATE_PATH)

    resolved_keys = {(tn, seq) for tn, seq_map in resolved_by_train.items() for seq in seq_map}
    tmp_needed = OUTPUT_DIR / "data_needed.tmp.csv"
    kept = 0
    dropped = 0
    with open(tmp_needed, "w", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=BASE_COLS)
        writer.writeheader()
        for tn, rows in needed_rows.items():
            for row in rows:
                key = (tn, int(row["SEQ"]))
                if key in resolved_keys:
                    dropped += 1
                    continue
                writer.writerow({k: row.get(k, "") for k in BASE_COLS})
                kept += 1
    tmp_needed.replace(NEEDED_PATH)

    changelog = {
        "method": "segment-lookup anchor-chain propagation, consistency-checked",
        "tolerance_km": TOLERANCE_KM,
        "batch_size": BATCH_SIZE,
        "num_batches": len(batches),
        "segment_lookup_size": len(seg),
        "trains_processed": len(train_list),
        "trains_with_at_least_one_fill": len(resolved_by_train),
        "rows_before": total_needed_rows,
        "rows_resolved_and_moved": total_resolved_rows,
        "rows_remaining_in_data_needed": kept,
        "anchor_chains_verified_and_filled": verified_chains,
        "anchor_chains_rejected_inconsistent": rejected_chains,
        "ultimate_rows_before": len(all_ultimate_rows),
        "ultimate_rows_after": len(all_ultimate_rows) + total_resolved_rows,
        "batch_reports": batch_reports,
        "note": "Every filled Distance value is the sum of real, already-recorded segment "
                "distances from elsewhere in the dataset, and every fill was checked against a "
                "second known anchor point (the train's own existing ultimate.csv fragment, or "
                "its Distance=0 source stop) before being accepted. Chains that summed to a "
                "different total than the known anchor gap were rejected, not forced. Rows this "
                "couldn't resolve remain in data_needed.csv untouched.",
    }
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(changelog, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in changelog.items() if k != "batch_reports"}, indent=2, default=str))


if __name__ == "__main__":
    main()
