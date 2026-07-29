"""
Tests for validator.py's DatasetValidator.

This module exists because a real bug slipped through here once already:
the first version of DatasetValidator hard-required station_code for every
dataset, which incorrectly flagged a legitimate per_train-shaped dataset as
broken (found and fixed by actually running the tool against the real
input files - see rail-dataset-analyzer's git history / project memory).
These tests exist so that class of regression gets caught automatically
next time, instead of requiring another manual run against real data to
notice.
"""

import pandas as pd

from validator import DatasetValidator


def make_per_stop_df(rows):
    return pd.DataFrame(rows, columns=[
        "train_number", "station_code", "Sequence",
    ])


def make_per_train_df(rows):
    return pd.DataFrame(rows, columns=[
        "train_number", "source_station", "destination_station",
        "intermediate_stops",
    ])


class TestShapeDetection:

    def test_detects_per_stop_shape(self):
        df = make_per_stop_df([
            ["12345", "NDLS", 1],
            ["12345", "AGC", 2],
        ])

        report = DatasetValidator().validate(df)

        assert report["shape"] == "per_stop"
        assert report["errors"] == []

    def test_detects_per_train_shape(self):
        df = make_per_train_df([
            ["12345", "NDLS", "MMCT", "AGC|BPL"],
        ])

        report = DatasetValidator().validate(df)

        assert report["shape"] == "per_train"
        assert report["errors"] == []

    def test_per_train_dataset_is_not_flagged_for_missing_station_code(self):
        # Regression test for the exact bug described in the module
        # docstring above: a per_train dataset has no station_code column
        # at all by design (it uses source_station/destination_station
        # instead), so validation must not require one.
        df = make_per_train_df([
            ["12345", "NDLS", "MMCT", ""],
        ])

        report = DatasetValidator().validate(df)

        assert "station_code" not in report["missing_required_fields"]
        assert report["errors"] == []

    def test_unrecognizable_dataset_produces_an_error_not_a_crash(self):
        df = pd.DataFrame({"some_column": [1, 2, 3]})

        report = DatasetValidator().validate(df)

        assert report["shape"] == "unknown"
        assert len(report["errors"]) == 1


class TestRequiredFields:

    def test_per_stop_missing_sequence_column_is_an_error(self):
        df = pd.DataFrame({
            "train_number": ["12345"],
            "station_code": ["NDLS"],
        })

        report = DatasetValidator().validate(df)

        assert report["shape"] == "unknown"
        assert report["errors"]


class TestDuplicateDetection:

    def test_per_stop_flags_duplicate_train_sequence_pairs(self):
        df = make_per_stop_df([
            ["12345", "NDLS", 1],
            ["12345", "AGC", 1],  # duplicate sequence for the same train
        ])

        report = DatasetValidator().validate(df)

        assert report["statistics"]["duplicate_train_sequence_pairs"] == 1
        assert any("sequence" in w for w in report["warnings"])

    def test_per_train_flags_duplicate_train_numbers(self):
        df = make_per_train_df([
            ["12345", "NDLS", "MMCT", ""],
            ["12345", "NDLS", "MMCT", ""],
        ])

        report = DatasetValidator().validate(df)

        assert report["statistics"]["duplicate_train_number_rows"] == 1

    def test_clean_dataset_reports_zero_duplicates(self):
        df = make_per_stop_df([
            ["12345", "NDLS", 1],
            ["12345", "AGC", 2],
        ])

        report = DatasetValidator().validate(df)

        assert report["statistics"]["duplicate_train_sequence_pairs"] == 0
        assert report["statistics"]["duplicate_rows"] == 0


class TestBlankValueDetection:

    def test_flags_blank_required_field(self):
        df = make_per_stop_df([
            ["12345", "", 1],
            ["12345", "AGC", 2],
        ])

        report = DatasetValidator().validate(df)

        assert report["statistics"]["blank_required_field_counts"]["station_code"] == 1
        assert any("blank" in w for w in report["warnings"])


class TestStatistics:

    def test_per_stop_stop_count_statistics(self):
        df = make_per_stop_df([
            ["12345", "NDLS", 1],
            ["12345", "AGC", 2],
            ["12345", "BPL", 3],
            ["54321", "NDLS", 1],
        ])

        report = DatasetValidator().validate(df)
        stats = report["statistics"]

        assert stats["unique_trains"] == 2
        assert stats["unique_stations"] == 3
        assert stats["max_stops_for_a_train"] == 3
        assert stats["min_stops_for_a_train"] == 1

    def test_per_train_stop_count_derived_from_packed_intermediate_stops(self):
        df = make_per_train_df([
            # 2 packed stops + source + destination = 4
            ["12345", "NDLS", "MMCT", "AGC|BPL"],
            # 0 packed stops + source + destination = 2
            ["54321", "NDLS", "AGC", ""],
        ])

        report = DatasetValidator().validate(df)
        stats = report["statistics"]

        assert stats["avg_stops_per_train"] == 3.0
        assert stats["max_stops_for_a_train"] == 4
        assert stats["min_stops_for_a_train"] == 2
