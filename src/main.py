import argparse
import json
import os

from loader import load_dataset
from station_master import load_station_master
from validator import DatasetValidator

from migration_engine import MigrationEngine
from exporter import DatasetExporter


def print_validation_report(report):

    print(f"\n--- {report['label']} ---")
    print(f"Rows    : {report['total_rows']}")
    print(f"Columns : {report['total_columns']}")

    if report["errors"]:
        print("ERRORS:")
        for error in report["errors"]:
            print(f"  - {error}")
        return

    if report["warnings"]:
        print("WARNINGS:")
        for warning in report["warnings"]:
            print(f"  - {warning}")
    else:
        print("No warnings.")

    print("Statistics:")
    for key, value in report["statistics"].items():
        print(f"  {key}: {value}")


def run_validation(args):

    validator = DatasetValidator()
    reports = []

    if args.old:
        old_df = load_dataset(args.old)
        reports.append(validator.validate(old_df, label=f"OLD: {args.old}"))

    if args.new:
        new_df = load_dataset(args.new)
        reports.append(validator.validate(new_df, label=f"NEW: {args.new}"))

    print("=" * 70)
    print("RailLens Dataset Validation")
    print("=" * 70)

    for report in reports:
        print_validation_report(report)

    os.makedirs("output", exist_ok=True)
    report_path = os.path.join("output", "validation_report.json")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=4)

    print(f"\nGenerated: {report_path}")


def main():

    parser = argparse.ArgumentParser(
        description="RailLens Dataset Migration Engine"
    )

    parser.add_argument(
        "--old",
        required=False,
        help="Old RailLens dataset"
    )

    parser.add_argument(
        "--new",
        required=False,
        help="New railway dataset"
    )

    parser.add_argument(
        "--station-master",
        default="input/station_master.csv",
        help="Station master CSV"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Only run structural validation and print dataset statistics "
            "(row/column counts, duplicate detection, blank required "
            "fields) for --old and/or --new, without running a migration. "
            "Does not require --station-master."
        )
    )

    args = parser.parse_args()

    if args.validate:

        if not args.old and not args.new:
            parser.error("--validate requires at least one of --old or --new")

        run_validation(args)
        return

    if not args.old or not args.new:
        parser.error("--old and --new are required unless --validate is used alone")

    print("=" * 70)
    print("RailLens Dataset Migration Engine")
    print("=" * 70)

    #
    # Load datasets
    #

    print("\nLoading datasets...")

    old_df = load_dataset(args.old)

    print("\nOld Dataset Columns:")
    print(old_df.columns.tolist())

    new_df = load_dataset(args.new)

    station_master = load_station_master(
        args.station_master
    )

    print("Datasets loaded successfully.\n")

    #
    # Migration
    #

    engine = MigrationEngine(
        station_master
    )

    import_rows, stats = engine.migrate(
        old_df,
        new_df
    )

    #
    # Export
    #

    exporter = DatasetExporter()

    exporter.export_import_dataset(
    import_rows
    )

    exporter.export_summary(
        stats
    )

    #
    # Summary
    #

    print()

    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)

    print(f"New Trains       : {stats['new']}")
    print(f"Updated Trains   : {stats['updated']}")
    print(f"Unchanged Trains : {stats['unchanged']}")
    print(f"Missing Trains   : {stats['missing']}")

    print()

    print(f"Rows Generated : {len(import_rows)}")

    print()

    print("Done.")


if __name__ == "__main__":
    main()