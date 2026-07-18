import argparse

from loader import load_dataset
from station_master import load_station_master

from migration_engine import MigrationEngine
from exporter import DatasetExporter


def main():

    parser = argparse.ArgumentParser(
        description="RailLens Dataset Migration Engine"
    )

    parser.add_argument(
        "--old",
        required=True,
        help="Old RailLens dataset"
    )

    parser.add_argument(
        "--new",
        required=True,
        help="New railway dataset"
    )

    parser.add_argument(
        "--station-master",
        default="input/station_master.csv",
        help="Station master CSV"
    )

    args = parser.parse_args()

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