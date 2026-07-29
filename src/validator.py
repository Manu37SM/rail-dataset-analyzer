"""
Dataset validation and statistics.

PROMPT.md names "Dataset validation", "Duplicate detection" and "Dataset
statistics" as core things rail-dataset-analyzer should provide, alongside
the comparison/migration pipeline it already has. Until now the tool only
ever looked at a dataset in the context of comparing it against another one
(MigrationEngine) - there was no way to just point it at a single CSV and
ask "is this file structurally sound, and what does it actually contain?"

This module answers that question on its own, independent of the migration
pipeline, so it can be run against a freshly-received dataset before
deciding whether it's even worth feeding into a migration at all.
"""

from column_detector import (
    find_column,
    TRAIN_NUMBER_COLUMNS,
    TRAIN_NAME_COLUMNS,
    STATION_CODE_COLUMNS,
    STATION_NAME_COLUMNS,
    SEQ_COLUMNS,
    ARRIVAL_COLUMNS,
    DEPARTURE_COLUMNS,
    DISTANCE_COLUMNS,
    SOURCE_COLUMNS,
    DESTINATION_COLUMNS,
)


# Logical field name -> candidate column list, reusing the same detection
# lists the parsers already rely on so "does this dataset look parseable"
# is judged by the exact same rules that will later try to parse it.
FIELD_CANDIDATES = {
    "train_number": TRAIN_NUMBER_COLUMNS,
    "train_name": TRAIN_NAME_COLUMNS,
    "station_code": STATION_CODE_COLUMNS,
    "station_name": STATION_NAME_COLUMNS,
    "sequence": SEQ_COLUMNS,
    "arrival_time": ARRIVAL_COLUMNS,
    "departure_time": DEPARTURE_COLUMNS,
    "distance": DISTANCE_COLUMNS,
    "source_station": SOURCE_COLUMNS,
    "destination_station": DESTINATION_COLUMNS,
}

# This tool has to deal with two genuinely different dataset shapes (see
# old_schedule_parser.py vs schedule_parser.py):
#
#   "per_stop"  - one row per (train, station) stop, identified by having
#                 both a station code and a sequence number. This is what
#                 OldScheduleParser expects.
#   "per_train" - one row per train, with source/destination columns and an
#                 optional packed "intermediate_stops" column. This is what
#                 ScheduleParser (the "new" format) expects.
#
# A dataset only has to satisfy the required fields for the shape it
# actually is - requiring station_code/sequence on a per-train dataset (or
# vice versa) would flag perfectly valid, parseable data as broken.
REQUIRED_FIELDS_BY_SHAPE = {
    "per_stop": ["train_number", "station_code", "sequence"],
    "per_train": ["train_number", "source_station", "destination_station"],
}


class DatasetValidator:

    def validate(self, df, label="dataset"):

        report = {
            "label": label,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "shape": None,
            "detected_columns": {},
            "missing_required_fields": [],
            "errors": [],
            "warnings": [],
            "statistics": {},
        }

        detected = self._detect_columns(df, report)
        shape = self._detect_shape(detected)
        report["shape"] = shape or "unknown"

        required_fields = REQUIRED_FIELDS_BY_SHAPE.get(shape, [])
        missing = [f for f in required_fields if not detected.get(f)]
        report["missing_required_fields"] = missing

        # A dataset missing a required field can't go any further - the
        # rest of these checks all assume the columns they need exist, so
        # bail out early with a clear reason rather than a confusing
        # downstream KeyError.
        if shape is None:
            report["errors"].append(
                "Could not determine dataset shape - it has neither a "
                "(station code + sequence) per-stop layout nor a "
                "(source + destination station) per-train layout. "
                f"Detected columns: {report['detected_columns']}"
            )
            return report

        if missing:
            report["errors"].append(
                f"Dataset looks like a '{shape}' layout but is missing "
                "required column(s): " + ", ".join(missing)
                + " - cannot be parsed into schedules as-is."
            )
            return report

        self._check_duplicates(df, detected, report, shape)
        self._check_blank_values(df, detected, report, required_fields)
        self._compute_statistics(df, detected, report, shape)

        return report

    # ------------------------------------------------------------

    def _detect_columns(self, df, report):

        detected = {}

        for field, candidates in FIELD_CANDIDATES.items():

            column = find_column(df, candidates)

            detected[field] = column
            report["detected_columns"][field] = column

        return detected

    def _detect_shape(self, detected):
        """
        Decide which of the two schedule layouts this dataset matches
        (see the module-level comment on REQUIRED_FIELDS_BY_SHAPE), based
        on which of their required columns are actually present. Checked
        in this order because a dataset could technically have leftover
        source/destination columns alongside a proper per-stop layout -
        per_stop is the more specific match.
        """

        if all(detected.get(f) for f in REQUIRED_FIELDS_BY_SHAPE["per_stop"]):
            return "per_stop"

        if all(detected.get(f) for f in REQUIRED_FIELDS_BY_SHAPE["per_train"]):
            return "per_train"

        return None

    # ------------------------------------------------------------

    def _check_duplicates(self, df, detected, report, shape):

        # Fully duplicated rows - almost always a sign the same CSV rows
        # got appended twice (e.g. a bad re-run of an export script).
        duplicate_row_count = int(df.duplicated().sum())

        if duplicate_row_count > 0:
            report["warnings"].append(
                f"{duplicate_row_count} fully duplicated row(s) found."
            )

        report["statistics"]["duplicate_rows"] = duplicate_row_count

        train_col = detected["train_number"]

        if shape == "per_stop":

            # Duplicate (train, sequence) pairs are a real data-integrity
            # problem even if the rows aren't identical - it means two
            # stops claim the same position in the same train's route,
            # which the backend's unique-per-sequence assumptions don't
            # tolerate.
            seq_col = detected["sequence"]

            duplicate_sequence_count = int(
                df[[train_col, seq_col]].duplicated().sum()
            )

            if duplicate_sequence_count > 0:
                report["warnings"].append(
                    f"{duplicate_sequence_count} row(s) share the same "
                    "(train number, sequence) pair - these will collide "
                    "on import."
                )

            report["statistics"]["duplicate_train_sequence_pairs"] = (
                duplicate_sequence_count
            )

        elif shape == "per_train":

            # In this layout, one row *is* one train, so a duplicate train
            # number means two full rows describing the same train.
            duplicate_train_count = int(df[train_col].duplicated().sum())

            if duplicate_train_count > 0:
                report["warnings"].append(
                    f"{duplicate_train_count} row(s) repeat a train number "
                    "already seen earlier in the file."
                )

            report["statistics"]["duplicate_train_number_rows"] = (
                duplicate_train_count
            )

    # ------------------------------------------------------------

    def _check_blank_values(self, df, detected, report, required_fields):

        blank_counts = {}

        for field in required_fields:

            column = detected.get(field)

            if not column:
                continue

            blank_count = int(
                (df[column].astype(str).str.strip() == "").sum()
            )

            blank_counts[field] = blank_count

            if blank_count > 0:
                report["warnings"].append(
                    f"{blank_count} row(s) have a blank '{field}' value."
                )

        report["statistics"]["blank_required_field_counts"] = blank_counts

    # ------------------------------------------------------------

    def _compute_statistics(self, df, detected, report, shape):

        stats = report["statistics"]

        train_col = detected["train_number"]
        station_col = detected["station_code"]

        stats["unique_trains"] = int(df[train_col].nunique())

        if station_col:
            stats["unique_stations"] = int(df[station_col].nunique())

        if shape == "per_stop":

            seq_col = detected["sequence"]

            rows_per_train = df.groupby(train_col)[seq_col].count()

            stats["avg_stops_per_train"] = round(
                float(rows_per_train.mean()), 2
            )
            stats["max_stops_for_a_train"] = int(rows_per_train.max())
            stats["min_stops_for_a_train"] = int(rows_per_train.min())

        elif shape == "per_train":

            # This layout packs intermediate stops into a single delimited
            # column rather than one row per stop, so "stops per train"
            # has to be derived by counting delimiters instead of grouping
            # rows.
            if "intermediate_stops" in df.columns:

                stop_counts = df["intermediate_stops"].fillna("").apply(
                    lambda value: (
                        len([s for s in value.split("|") if s.strip()])
                        if value.strip() else 0
                    )
                )

                # +2 for the source and destination stops that this format
                # stores in their own dedicated columns rather than in
                # intermediate_stops.
                stops_per_train = stop_counts + 2

                stats["avg_stops_per_train"] = round(
                    float(stops_per_train.mean()), 2
                )
                stats["max_stops_for_a_train"] = int(stops_per_train.max())
                stats["min_stops_for_a_train"] = int(stops_per_train.min())
