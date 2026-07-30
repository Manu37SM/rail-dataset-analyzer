# RailLens Dataset — Validation & Audit Report

**Dataset:** `train_dataset_original.csv`
**Audit date:** 2026-07-30
**Auditor:** Claude (Anthropic), automated pipeline in `scripts/`

---

## 1. Honest scope statement (read this first)

The original request asked for verification against "official Indian Railways / CRIS / NTES / data.gov.in" data. In practice, **none of those sources offer a bulk, programmatically-fetchable dataset**:

| Source | Status |
|---|---|
| **data.gov.in** (Ministry of Railways, "Railway Station" catalog) | Attempted directly. The catalog page returns **"No Result Found"** for any downloadable resource without an authenticated login, and the portal itself currently displays a banner stating it is *"a sandbox environment created for testing and demonstration purposes only... may be incomplete or inaccurate."* Last updated 2015. **Not usable.** |
| **NTES** (enquiry.indianrail.gov.in) | Live single-train/single-station lookup only — no bulk export. Querying all 11,113 trains and 8,151 stations individually was not feasible in this session. **Not usable at scale.** |
| **CRIS** | No public bulk dataset endpoint found. **Not usable.** |
| **datameet/railways** (GitHub) | A **community-crowdsourced** dataset (~2015–2016 vintage), not an official government publication, but genuinely bulk-fetchable (8,990 stations, 5,208 trains). **Used**, explicitly labeled as non-official throughout. |
| **mayurrawte/IndianRailApi station_codes.json** (GitHub) | Community-compiled station name→code list (10,307 entries). **Used only as a fallback** when the primary reference had no match. |

**Bottom line:** every "VERIFIED" status in this report means *"consistent with a community-maintained reference dataset,"* not *"certified by Indian Railways."* Nothing was fabricated or inferred to fill this gap — anything that couldn't be checked against a real source is explicitly marked **Requires Manual Verification**, per your instructions.

---

## 2. Summary numbers

| Metric | Value |
|---|---|
| Total records checked | 186,124 |
| Total unique trains | 11,113 |
| Total unique station codes | 8,151 |
| Records updated (values changed) | 5 |
| Records removed | 5 (malformed duplicate fragments, see §3.1) |
| Records added | 0 |
| Records requiring manual verification (station-level) | 50,644 rows / 186,119 (27.2%) — driven mostly by name-spelling differences vs. a decade-old community reference, not confirmed errors |
| Records requiring manual verification (train-level) | 7,177 of 11,113 trains (64.6%) — see §4.2, this is expected given reference dataset age |
| Data quality score | **81.5 / 100** (methodology in §6) |

---

## 3. Internal structural audit (100% coverage, all 186,124 rows)

Script: `scripts/01_internal_audit.py` — reusable, deterministic, checks every row.

### 3.1 Critical findings (fixed)

**5 "split row" corruptions.** Trains 6919, 6920, 56905, 56906, 57641 each had one stop (station **KGIH / Kalgurki Halt**) split across two physical CSV lines: the first line had the correct Train No/SEQ/Station Code/Name but `NA` placeholders for arrival, departure, distance, and source/destination; the very next line carried the missing values but with a garbage `Train No` of literally `"K"` and all other fields shifted one column left.

Example (train 6919, before):
```
6919,UBL-BJP SPL,33,KGIH,KALGURKI H,NA,NA,NA,NA,NA,NA,NA
K,12:16:00,12:17:00,214,UBL,HUBLI JN.,BJP,BIJAPUR JN,NA,NA,NA,NA
```
After reconstruction (both fragments merged into one row, second row removed):
```
6919,UBL-BJP SPL,33,KGIH,KALGURKI H,12:16:00,12:17:00,214,UBL,HUBLI JN.,BJP,BIJAPUR JN
```
This is a **mechanical reconstruction**, not a guess: every value used already existed verbatim in the source file. Full before/after/reason for all 5 rows is in `data/output/cleaning_changelog.json`.

**1 SEQ discontinuity** — was entirely caused by the "K" row above; resolved automatically once that row was removed. Confirmed 0 remaining after fix.

### 3.2 Findings left as-is and flagged (not auto-corrected)

| Category | Rows affected | Why not auto-fixed |
|---|---:|---|
| Origin arrival ≠ `00:00:00` placeholder | 9,162 | Genuinely ambiguous: some trains use `00:00:00` at origin, others duplicate the departure time as arrival. Both are plausible internal conventions; the "correct" one can't be determined without an official schedule. Requires Manual Verification. |
| Terminus departure ≠ `00:00:00` placeholder | 9,158 | Same reasoning as above. |
| `CSTM`/`CSMT` code alias inconsistency | 921 (across 921 trains) | Both codes genuinely refer to the same station, Mumbai Chhatrapati Shivaji Maharaj Terminus — confirmed by web search, though sources themselves disagree on which is "primary" today (some cite CSTM as the mainline code, others cite CSMT as current post-2017-rename code). Because official sources conflict, we did **not** pick a winner and overwrite data — this is flagged as a known, benign naming inconsistency for a human to resolve with a definitive NTES/CRIS lookup. |
| Encoding / stray-whitespace issues in Station Name | 694 | Cosmetic; left untouched to avoid altering data without a clear correct value. |
| Station Code fails expected 2–6 char alphanumeric pattern | 471 (6 unique codes: single-letter codes `R`, `G` used for Raipur Jn / Gondia Jn on certain trains) | Ambiguous — could be legitimate short-form codes used inconsistently in the source system. Requires Manual Verification. |
| Departure before Arrival at intermediate stop | 124 | May be a legitimate overnight halt spanning midnight; this dataset has no day-offset field, so it's impossible to tell from the data alone whether this is an error. |
| Same station appearing twice on one train | 60 (across several trains) | Could be a legitimate loop/circular route. Requires Manual Verification. |
| Source/Destination Station mismatch (genuine, not CSTM/CSMT) | 4 (trains 7062, 8064) | The declared Source/Destination for these two trains doesn't match their actual first/last stop in the data (e.g. train 8064 "BQA-KGP DEMU" is declared Source=BQA/Dest=KGP but actually runs YPR→...→HWH). This looks like a genuine data-entry error in the source file, but we have no way to know the *correct* value without an authoritative schedule. **Requires Manual Verification** — left completely unchanged. |
| Station Code mapped to >1 Station Name in dataset (self-inconsistency) | 0 | — |
| Station Name mapped to >1 Station Code in dataset | 47 names | Likely distinct stations sharing a name (common in India) or legitimate code changes. Requires Manual Verification. |

### 3.3 Systemic finding: 12-character truncation on Station Name

The dataset's `Station Name` field is **hard-capped at 12 characters** — confirmed by measuring every row (`max()` == 12 across all 186,124 rows), with **51,145 rows (27.5%)** sitting exactly at that cap (e.g. `"MADGOAN JN."`, `"DELHI-SAFDAR"`, `"RAJENDRANAGA"`). This single systemic issue explains a large share of the "name mismatch" findings below — it is a source-system limitation, not per-row data corruption, and nothing was done to "fix" the original column (see §5).

---

## 4. External cross-reference (bulk, community-sourced)

Script: `scripts/02_external_crossref.py`. Reference: datameet/railways + secondary station-code list (see §1 for sourcing caveats).

### 4.1 Station-level (8,151 unique station codes)

| Status | Count | % |
|---|---:|---:|
| `VERIFIED` (exact name match) | 4,894 | 60.0% |
| `VERIFIED_TRUNCATED_IN_SOURCE` (dataset name is a truncation-consistent prefix of the reference name) | 775 | 9.5% |
| `VERIFIED_SECONDARY_SOURCE_ONLY` | 354 | 4.3% |
| `NAME_MISMATCH_REQUIRES_MANUAL_VERIFICATION` | 2,011 | 24.7% |
| `REQUIRES_MANUAL_VERIFICATION` (secondary source, name didn't match) | 83 | 1.0% |
| `NOT_FOUND_IN_ANY_REFERENCE_REQUIRES_MANUAL_VERIFICATION` | 34 | 0.4% |

Spot-checking the 2,011 name mismatches shows most fall into three buckets, none of which is a clear "dataset is wrong" case:
- **Truncation** below the 12-char boundary check's confidence threshold (e.g. very short names that still got cut)
- **Genuine historical renames** the reference dataset itself may or may not reflect (e.g. Quilon→Kollam Jn, Alwaye→Aluva, Trichur→Thrisur — these are real IR renames, and it's not always clear which era each source reflects)
- **Transliteration variants** (Vizianagaram/Vizianagram, Rajahmundry/Rajamundry)

None of these were auto-corrected. Full row-level detail: `data/output/station_crossref.csv`.

### 4.2 Train-level (11,113 unique train numbers)

| Status | Count | % |
|---|---:|---:|
| `VERIFIED_PRESENT` in datameet reference | 3,936 | 35.4% |
| `NOT_IN_2016_REFERENCE...REQUIRES_MANUAL_VERIFICATION` | 7,177 | 64.6% |

**This low match rate is expected, not alarming.** The datameet train reference is ~10 years old (circa 2015-2016) and only has train-level metadata (name/zone/from/to), not full timetables. Indian Railways introduces, renumbers, and withdraws thousands of trains per decade (including a mass 2019-2020 renumbering and ongoing Vande Bharat/special-service additions), so a majority-unmatched rate against a decade-old list is exactly what you'd expect from a currently-maintained dataset — it is *not* evidence that 65% of this dataset's trains are wrong. Full detail: `data/output/train_crossref.csv`.

### 4.3 Fields that could not be checked at all

The source CSV has **no Railway Zone, Division, State, or Platform columns**. These were requested for verification but don't exist in the schema, so there was nothing to check or synchronize. If you want these added, they could be populated from the datameet station reference (which has Zone/State) as a new enrichment column, using the same non-destructive approach as `Station Name (Community Reference)` — this hasn't been done since it wasn't part of the original schema and would need your sign-off on adding new columns.

---

## 5. What was actually changed in the data

Script: `scripts/03_apply_fixes.py`. Output: `data/output/train_dataset_cleaned.csv`.

1. **5 rows reconstructed, 5 rows removed** (net: 186,124 → 186,119 rows) — the split-row corruption fix described in §3.1. Every original column value involved was already present in the file; nothing was invented.
2. **Two new columns appended, nothing existing altered:**
   - `Validation Status` — per-row rollup of the Station Code's cross-reference outcome (see §4.1 statuses), so you can filter instantly.
   - `Station Name (Community Reference)` — populated **only** for the 775 `VERIFIED_TRUNCATED_IN_SOURCE` rows, giving the untruncated name from the community reference. Left blank everywhere else. **The original `Station Name` column was not touched or overwritten anywhere.**

No station codes, train numbers, distances, timestamps, or names were altered, guessed, or removed outside of the 5 rows above.

---

## 6. Data quality score: 81.5 / 100

Calculated transparently as a 50/50 composite (not a black-box number):

- **Structural integrity: 89.0%** — percentage of rows with zero internal-consistency flags of any kind (`(186,124 − 20,450) / 186,124`). Note most flags are low-severity conventions/ambiguities (§3.2), not confirmed defects — only 14 rows carry a `critical` flag post-fix.
- **External verifiability: 73.9%** — percentage of unique station codes matched (exactly or via confident truncation/secondary match) against the community bulk reference (`(4,894 + 775 + 354) / 8,151`).

Train-level match rate (35.4%) was **excluded** from the score, since the reference dataset's age makes low train coverage expected rather than a quality signal (§4.2).

---

## 7. Recommendations for future updates

1. **Get a real official source.** The single highest-value next step is obtaining CRIS/NTES bulk data through a proper channel (an official API key, a formal RTI/data request, or a more recent OGD dataset if the Ministry of Railways re-publishes one) — everything in this report is capped by community-source reliability until that happens.
2. **Resolve the CSTM/CSMT question definitively** with one authoritative NTES lookup, then decide a canonical code and re-run `03_apply_fixes.py` with that rule added — currently a genuinely open question across sources.
3. **Manually verify trains 7062 and 8064's Source/Destination Station values** — these are the only two trains with an unexplained, likely-genuine data-entry inconsistency.
4. **Consider whether to add Zone/Division/State columns** from the datameet reference (or a better future source) — schema currently doesn't support this.
5. **Re-run the whole pipeline whenever a newer bulk dataset becomes available** — all three scripts (`01_internal_audit.py`, `02_external_crossref.py`, `03_apply_fixes.py`) are parameterized/reusable, not one-off.
6. If a newer, clearly superior bulk dataset is found (e.g. an updated datameet fork, or an official release), it should **replace** the current community reference in `data/reference/` — no such dataset was identified during this run; datameet/railways remains the best available option.

---

## 8. Files produced

```
data/output/train_dataset_cleaned.csv      -- cleaned dataset (5 rows fixed, 2 columns added)
data/output/internal_audit_flags.csv       -- every row-level flag (20,450 rows, pre-clean)
data/output/internal_audit_summary.json    -- aggregate counts
data/output/station_crossref.csv           -- per-station-code verification status
data/output/train_crossref.csv             -- per-train-number verification status
data/output/external_crossref_summary.json -- aggregate counts + source disclosures
data/output/cleaning_changelog.json        -- full before/after for every changed row
scripts/01_internal_audit.py               -- reusable, run on any RailLens-format CSV
scripts/02_external_crossref.py            -- reusable, swap in new reference files as they appear
scripts/03_apply_fixes.py                  -- reusable, conservative-by-design
```
