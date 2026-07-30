# RailLens Dataset — Addendum: Dataset 2 Validation & Merge Report

**Covers:** `train_dataset_cleaned.csv` (as newly uploaded — hereafter "**dataset 2**", distinct from the *output* of the first audit, hereafter "**dataset 1**") and the merge of both into one combined dataset.
**Date:** 2026-07-30
**Read alongside:** `AUDIT_REPORT.md` (dataset 1's original audit — methodology, source disclosures, and caveats there all still apply).

---

## 1. What dataset 2 actually was

Despite the filename, this is a **different dataset** from dataset 1's output — different row count (178,209 vs. 186,124), different train/station coverage (8,366 trains / 7,061 stations vs. 11,113 / 8,151), a different column name (`Arrival Time` vs `Arrival time`), a different time format (`7:24` vs `07:24:00`), and a **95.3% missing `Distance` column**. It appears to be a separately-sourced schedule export with its own set of data-quality issues, not a copy of dataset 1.

## 2. Normalization (cosmetic only, `scripts/00_normalize_ds2.py`)

- Renamed `Arrival Time` → `Arrival time` for schema consistency.
- Reformatted 166,999 arrival times and 169,623 departure times from `H:MM`/`HH:MM` to `HH:MM:SS` — zero-padding and appending `:00` seconds. Blanks were left blank.
- Stripped a stray trailing `" Train"` token from 139,719 `Train Name` values (e.g. `"BJU LJN EXP Train"` → `"BJU LJN EXP"`) — purely cosmetic, doesn't affect any matching/merge key.

## 3. Internal structural audit findings unique to dataset 2

Dataset 2 had two genuine structural problems dataset 1 didn't:

### 3.1 "Adjacent duplicate stops" (3,532 flagged rows)

The same Station Code appeared twice in a row (consecutive SEQ) for over a thousand trains. Investigating every pair field-by-field split them three ways:

| Type | Count | Action |
|---|---:|---|
| **Identical** (exact duplicate in every timing/distance field) | 497 | Second occurrence dropped |
| **Complementary** (no conflicting values — e.g. one row has Departure Time, the other has Distance) | 184 | Merged into one row, same non-destructive reconstruction principle used for dataset 1's split rows in the original audit |
| **Conflicting** (the two rows disagree on a value) | 509 | **Left untouched, flagged for manual verification** — picking a winner would be a guess |

The remaining ~2,342 duplicate-stop rows are non-adjacent (same station appears twice, but not back-to-back) and, as with dataset 1, may be legitimate loop/circular routes — left alone.

### 3.2 Single-letter station codes (4,485 rows, 22 unique letters A–Y)

Every single-letter code was confirmed to exactly equal the first letter of its Station Name (e.g. `"Jalna"` recorded with code `"J"`), and the same letter is reused across dozens of unrelated real stations — e.g. code `"S"` alone covers Sausar, Saoner, Supaul, Sulgare, and 46 other places. This is a genuine source-truncation bug, not a real code.

**The original `Station Code` column was left untouched** (we can't know the true code with certainty). Instead, a new column, `Station Code (Community Reference Suggestion)`, was added and populated **only** where the Station Name had a single, unambiguous match in the bulk reference data — this recovered a confident candidate code for **2,815 of the 4,485** affected rows. The remaining 1,670 have no unambiguous match and stay flagged.

## 4. External cross-reference (same sources/caveats as dataset 1 — see `AUDIT_REPORT.md` §1)

| Station-level (7,061 unique codes) | Count |
|---|---:|
| VERIFIED | 4,621 |
| VERIFIED_TRUNCATED_IN_SOURCE | 606 |
| VERIFIED_SECONDARY_SOURCE_ONLY | 241 |
| NAME_MISMATCH_REQUIRES_MANUAL_VERIFICATION | 1,485 |
| NOT_FOUND_IN_ANY_REFERENCE / REQUIRES_MANUAL_VERIFICATION | 108 |

| Train-level (8,366 unique numbers) | Count |
|---|---:|
| VERIFIED_PRESENT in reference | 3,807 |
| Not in ~2016 reference (expected — see dataset 1 report §4.2) | 4,559 |

## 5. Filling missing timing (`scripts/04_fill_and_merge.py`)

**Method:** for a given `(Train No, Station Code)`, if that exact pair appears in the *other* dataset and that dataset has a non-null Arrival time / Departure Time / Distance, the value is copied across — **only when the pair is unambiguous** (appears once) in the source dataset. Nothing is interpolated, computed, or estimated; every filled value already existed verbatim somewhere in one of the two files.

**Result — and an important honesty note:**
- Cross-filling **dataset 2 from dataset 1** successfully populated **86,476 Distance, 4,868 Arrival, and 4,026 Departure** values (visible in the standalone file `dataset2_filled_standalone.csv`).
- Cross-filling **dataset 1 from dataset 2** filled **zero** values — dataset 1 turned out to already be 100% complete on these three fields after the original cleaning pass.
- **However**, because dataset 1 is already complete, it is chosen as the "kept" version for essentially every one of the 5,373 trains that appear in both datasets (see merge logic below) — which means those 86,476+ filled dataset-2 values, while real, mostly get **superseded by dataset 1's own already-complete data for the same trains** and don't end up in the final merged file. This is not a bug, just how the numbers fall out: dataset 1 didn't need the help for the trains it already had.
- The genuinely-unfillable gaps are the **2,993 trains that exist only in dataset 2**, which have no counterpart in dataset 1 to cross-reference against. These remain blank and are **not guessed** — the merged file's residual 23.2% missing Distance is concentrated almost entirely here.

## 6. Merge logic (`scripts/04_fill_and_merge.py`)

- **Train present in only one dataset:** all of that dataset's rows are kept as-is.
- **Train present in both datasets:** rather than splicing the two stop-lists together (which would require guessing a merged route order — explicitly avoided), **one dataset's full stop sequence is kept** for that train: whichever has fewer missing Arrival/Departure/Distance values after cross-filling, ties going to dataset 1. In practice dataset 1 was chosen for **all 5,373** overlapping trains, since it was already the more complete source. The other dataset's rows for that train are dropped from the merge (logged in `merge_changelog.json`).
- A final exact-duplicate-row safety pass ran on the combined file (found 0 additional exact duplicates — the train-level dedup above already prevented them).

## 7. Merged dataset — final numbers

| Metric | Value |
|---|---:|
| Dataset 1 rows contributed | 186,119 |
| Dataset 2 rows contributed | 60,263 (only non-overlapping trains) |
| **Final merged rows** | **246,382** |
| Final unique trains | 14,105 |
| Final unique stations | 8,255 |
| Missing Arrival time | 3,624 (1.5%) |
| Missing Departure Time | 3,009 (1.2%) |
| Missing Distance | 57,270 (23.2%) — concentrated in dataset-2-only trains |

New columns carried into the merged file: `Source Dataset` (which original file a row came from), `Timing Source` (whether a value was original or cross-filled, in the standalone files), `Validation Status`, `Station Name (Community Reference)`, `Station Code (Community Reference Suggestion)`.

## 8. What still needs manual verification

Everything already flagged in `AUDIT_REPORT.md` §3.2 for dataset 1, plus:
- 509 conflicting adjacent-duplicate stop pairs in dataset 2 (left as two separate rows).
- 1,670 single-letter station codes with no unambiguous reference match.
- 1,485 dataset-2 station name mismatches vs. the community reference.
- 57,270 rows with no Distance value and no cross-reference available (all dataset-2-only trains).
- The 2,993 dataset-2-only trains have not been checked against the community train reference for existence/validity beyond the crossref table in `train_crossref.csv`.

## 9. Files produced (in addition to dataset 1's originals)

```
raillens_validation2/data/train_dataset2_normalized.csv      -- schema/format normalized, nothing filled
raillens_validation2/data/train_dataset2_fixed.csv            -- + adjacent-duplicate fixes + code suggestions
raillens_validation2/data/output/*                             -- audit flags, crossref tables, changelogs
raillens_merged/data/output/train_dataset_merged.csv          -- ** the final combined, deduplicated dataset **
raillens_merged/data/output/dataset1_filled_standalone.csv    -- dataset 1 after cross-fill attempt (no change)
raillens_merged/data/output/dataset2_filled_standalone.csv    -- dataset 2 after cross-fill (86K+ values added)
raillens_merged/data/output/merge_changelog.json              -- full per-train merge decisions
raillens_merged/scripts/04_fill_and_merge.py                  -- reusable
```
