# RailLens Train Dataset — Validation Pipeline

## What this is

A validation, cleaning, and audit pipeline for `train_dataset_original.csv` — 186,124 rows covering 11,113 trains and 8,151 stations, in the format:

```
Train No, Train Name, SEQ, Station Code, Station Name, Arrival time, Departure Time,
Distance, Source Station, Source Station Name, Destination Station, Destination Station Name
```

## Dataset source

Provenance of the original CSV predates this audit and wasn't independently re-verifiable from within this session — treat it as the RailLens project's existing migrated dataset (per prior work: converted from an IRCTC-derived source, cross-referenced during migration against datameet/railways and trainhelp.in).

## Verification methodology

**Full details and honest caveats are in [`reports/AUDIT_REPORT.md`](reports/AUDIT_REPORT.md) — read that first.** Short version:

- **Internal structural audit**: 100% of rows checked for duplicates, missing values, SEQ/distance/timing consistency, referential integrity, formatting, and encoding — using only the file's own internal logic. No external source needed or used for this pass.
- **External cross-reference**: attempted official sources first (data.gov.in, NTES, CRIS) — none offered a usable bulk/download interface at the time of this run (see report §1 for exactly what was tried and why each failed). Fell back to **datameet/railways** and a secondary GitHub station-code list, both **community-crowdsourced, not official government data**. Every verification result is labeled accordingly.
- **Nothing was fabricated or guessed.** Anything that couldn't be checked against a real source, or that a source disagreed on, is marked `REQUIRES_MANUAL_VERIFICATION` and left untouched in the data.

## Cleaning process

Only two kinds of change were made to the data (full changelog: `data/output/cleaning_changelog.json`):

1. **5 rows mechanically reconstructed** — a source-file bug had split single logical rows into two physical CSV lines (visible as `Train No == "K"` on the corrupted fragment). Repaired by recombining data already present in the file; the malformed fragment rows were then removed. Net effect: 186,124 → 186,119 rows.
2. **2 new columns appended** (`Validation Status`, `Station Name (Community Reference)`) — purely additive, for transparency. **No existing column was altered, overwritten, or removed anywhere else in the dataset.**

## Last verified

**2026-07-30**, against datameet/railways as fetched on that date. data.gov.in and NTES were checked but had no usable bulk export at that time (report §1) — this should be re-attempted on future runs in case that changes.

## How to re-run

```bash
cd raillens_validation
python3 scripts/01_internal_audit.py --input data/train_dataset_original.csv
python3 scripts/02_external_crossref.py
python3 scripts/03_apply_fixes.py
```

To validate a *newer* dataset, point `--input` at the new file. To use a *newer* reference dataset, drop the new file(s) into `data/reference/` and update the paths at the top of `02_external_crossref.py`.

## Known limitations

- **No official government source was actually verifiable in bulk.** Every "verified" result in this pipeline is checked against community-maintained data (~2015–2016 vintage for the train list, likely more recently updated for the station list), not CRIS/NTES/Ministry of Railways directly. Treat this as a strong internal-consistency pass plus a best-effort external sanity check, not a certified-accurate dataset.
- **64.6% of trains (7,177 of 11,113) don't appear in the train reference** — this is expected given the reference's age (~10 years), not necessarily a dataset defect. See audit report §4.2.
- **No Zone / Division / State / Platform columns exist in the source schema** — these couldn't be verified or synchronized because there's nothing in the CSV to check. Could be added as enrichment columns from the station reference (which does have Zone/State) if desired — not done without explicit sign-off since it changes the schema.
- **2 trains (7062, 8064) have an unexplained Source/Destination Station mismatch** that looks like a genuine data-entry error but couldn't be corrected without an authoritative schedule to confirm the right value.
- **The `CSTM`/`CSMT` code question is genuinely unresolved** — both codes appear in the dataset for the same Mumbai terminus, and the sources checked for this report disagree on which is currently primary. Needs one definitive NTES lookup to settle.
- **12-character truncation on Station Name** is a source-system limitation affecting 27.5% of rows; not corrected in the original column (only offered as a separate, clearly-labeled suggestion column where confidently reconstructable).

## Directory structure

```
data/
  train_dataset_original.csv       -- original input, untouched
  reference/                       -- bulk reference datasets used for cross-check
    stations_datameet.json
    trains_datameet.json
    station_codes_secondary.json
  output/
    train_dataset_cleaned.csv      -- cleaned + enriched dataset (the deliverable)
    internal_audit_flags.csv
    internal_audit_summary.json
    station_crossref.csv
    train_crossref.csv
    external_crossref_summary.json
    cleaning_changelog.json
scripts/
  01_internal_audit.py
  02_external_crossref.py
  03_apply_fixes.py
reports/
  AUDIT_REPORT.md                  -- full findings, numbers, and recommendations
README.md                          -- this file
```
