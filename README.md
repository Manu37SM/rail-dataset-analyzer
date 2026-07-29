# RailLens Dataset Migration Engine

A Python tool for migrating and comparing railway schedule datasets. It parses old and new train schedule formats, detects changes (new trains, updated schedules, missing trains), and generates an import-ready dataset along with a migration summary.

## Features

- **Old & new schedule parsing** – Handles different CSV column layouts via `column_detector.py`
- **Station resolution** – Fuzzy-matches station names against a station master CSV using `rapidfuzz`
- **Schedule comparison** – Detects changes in train schedules (stops, timings, classes, running days)
- **Import-ready export** – Generates a normalized CSV suitable for database import
- **Migration reports** – Produces a summary JSON and CSV reports for missing/updated/new trains

## Requirements

- Python 3.10+
- pandas >= 2.2.0
- tabulate >= 0.9.0
- rapidfuzz >= 3.9.0

Install dependencies with:

```bash
pip install -r requirements.txt
```

For running the test suite, install the dev requirements instead (installs
pytest on top of the runtime ones above):

```bash
pip install -r requirements-dev.txt
```

## Usage

### Migration (compare old vs. new and produce import-ready output)

```bash
python src/main.py --old <old_dataset.csv> --new <new_dataset.csv> [--station-master input/station_master.csv]
```

### Validation only (no migration - just check whether a dataset is structurally sound)

Point this at a single dataset (or both) before deciding whether it's even
worth feeding into a migration. Detects the dataset's shape (`per_stop` vs
`per_train` - see `validator.py`), missing required columns, duplicate
rows/keys, blank required fields, and basic statistics (unique trains,
unique stations, stops per train).

```bash
python src/main.py --validate --old <old_dataset.csv> [--new <new_dataset.csv>]
```

Writes `output/validation_report.json` in addition to printing a summary.

### Arguments

| Argument           | Description                                      | Default                      |
|--------------------|--------------------------------------------------|------------------------------|
| `--old`            | Path to the old RailLens dataset CSV             | required unless `--validate` is used with only `--new` |
| `--new`            | Path to the new railway dataset CSV              | required unless `--validate` is used with only `--old` |
| `--station-master` | Path to station master CSV                       | `input/station_master.csv`   |
| `--validate`       | Run structural validation only (see above) instead of a full migration | off |

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests live in `tests/` and currently cover `validator.py` (dataset shape
detection, required-field checks, duplicate detection, statistics) and
`normalizer.py` (station/train name normalization rules). `tests/conftest.py`
adds `src/` to the import path so tests can import modules the same flat
way `main.py` does.

### Output

| File                        | Description                                      |
|-----------------------------|--------------------------------------------------|
| `output/import_ready.csv`   | Normalized train schedule data for import        |
| `output/migration_summary.json` | Summary counts (new, updated, unchanged, missing) |
| `output/missing_trains.csv` | List of trains present in the old set but missing from the new set |
| `output/new_trains.csv`     | List of trains new in the dataset                |
| `output/updated_trains.csv` | List of trains with schedule changes             |

## Project Structure

```
src/
├── main.py                  # Entry point (CLI)
├── column_detector.py       # Auto-detect CSV column mappings for old & new datasets
├── loader.py                # Dataset loading utilities
├── models.py                # Data classes (TrainRecord, StationMatch, ScheduleStop, etc.)
├── normalizer.py            # String/integer normalization helpers
├── station_master.py        # Station master CSV loader
├── station_resolver.py      # Fuzzy station name resolution against station master
├── schedule_parser.py        # Parser for the new schedule format
├── old_schedule_parser.py    # Parser for the old RailLens schedule format
├── schedule_comparator.py    # Compares old vs new schedules and detects changes
├── migration_builder.py      # Builds import-ready rows from parsed schedules
├── migration_engine.py       # Orchestrates the full migration pipeline
├── migration_report.py       # Generates summary and per-category CSV/JSON reports
├── exporter.py               # Exports results to CSV and JSON files
└── validator.py               # Standalone structural validation (--validate mode)

tests/
├── conftest.py               # Adds src/ to sys.path for tests
├── test_validator.py         # DatasetValidator tests
└── test_normalizer.py        # normalize_name() tests
```

## How It Works

1. **Load** – Old and new CSV datasets are loaded into DataFrames. Column layouts are auto-detected.
2. **Parse** – Each dataset is parsed into `TrainSchedule` objects with station stops, timings, classes, and running days.
3. **Resolve stations** – Station names are fuzzy-matched against the station master to obtain canonical station codes.
4. **Compare** – For each train number present in both datasets, schedules are compared field by field.
5. **Categorize** – Trains are categorized as **new**, **updated**, **unchanged**, or **missing**.
6. **Export** – Import-ready rows are built (with station sequence numbers) and written to CSV together with summary reports.

## License

MIT