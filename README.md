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

## Usage

```bash
python src/main.py --old <old_dataset.csv> --new <new_dataset.csv> [--station-master input/station_master.csv]
```

### Arguments

| Argument           | Description                                      | Default                      |
|--------------------|--------------------------------------------------|------------------------------|
| `--old`            | Path to the old RailLens dataset CSV             | (required)                   |
| `--new`            | Path to the new railway dataset CSV              | (required)                   |
| `--station-master` | Path to station master CSV                       | `input/station_master.csv`   |

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
└── exporter.py               # Exports results to CSV and JSON files
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