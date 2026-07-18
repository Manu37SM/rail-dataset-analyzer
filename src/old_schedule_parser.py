from collections import defaultdict

from column_detector import (
    find_column,
    TRAIN_NUMBER_COLUMNS,
    TRAIN_NAME_COLUMNS,
    STATION_CODE_COLUMNS,
    STATION_NAME_COLUMNS,
    ARRIVAL_COLUMNS,
    DEPARTURE_COLUMNS,
    DISTANCE_COLUMNS,
    SEQ_COLUMNS,
    SOURCE_COLUMNS,
    DESTINATION_COLUMNS,
    SOURCE_NAME_COLUMNS,
    DESTINATION_NAME_COLUMNS,
)

from models import ScheduleStop
from models import TrainSchedule


class OldScheduleParser:

    def parse(self, dataframe):

        train_col = find_column(dataframe, TRAIN_NUMBER_COLUMNS)
        train_name_col = find_column(dataframe, TRAIN_NAME_COLUMNS)
        seq_col = find_column(dataframe, SEQ_COLUMNS)
        station_code_col = find_column(dataframe, STATION_CODE_COLUMNS)
        station_name_col = find_column(dataframe, STATION_NAME_COLUMNS)
        arrival_col = find_column(dataframe, ARRIVAL_COLUMNS)
        departure_col = find_column(dataframe, DEPARTURE_COLUMNS)
        distance_col = find_column(dataframe, DISTANCE_COLUMNS)
        source_code_col = find_column(dataframe, SOURCE_COLUMNS)
        destination_code_col = find_column(dataframe, DESTINATION_COLUMNS)
        source_name_col = find_column(dataframe, SOURCE_NAME_COLUMNS)
        destination_name_col = find_column(dataframe, DESTINATION_NAME_COLUMNS)

        print("=" * 70)
        print("Detected Columns")
        print("=" * 70)
        print(f"Train Number : {train_col}")
        print(f"Train Name   : {train_name_col}")
        print(f"SEQ          : {seq_col}")
        print(f"Station Code : {station_code_col}")
        print(f"Station Name : {station_name_col}")
        print(f"Arrival      : {arrival_col}")
        print(f"Departure    : {departure_col}")
        print(f"Distance     : {distance_col}")
        print()

        train_map = defaultdict(list)

        #
        # Group rows by train
        #
        for _, row in dataframe.iterrows():

            train_no = str(row[train_col]).strip()

            train_map[train_no].append(row)

        schedules = {}

        #
        # Build schedule for each train
        #
        invalid_row_count = 0

        skipped_values = defaultdict(list)

        for train_no, rows in train_map.items():

            try:

                valid_rows = []

                for row in rows:

                    seq = str(row[seq_col]).strip()

                    if not seq.isdigit():
                        invalid_row_count += 1
                        skipped_values[seq].append(train_no)
                        continue

                    valid_rows.append(row)

                if not valid_rows:
                    continue

                rows = sorted(
                    valid_rows,
                    key=lambda r: int(str(r[seq_col]).strip())
                )

                stops = []

                for row in rows:

                    stops.append(
                        ScheduleStop(
                            sequence=int(str(row[seq_col]).strip()),
                            station_code=str(row[station_code_col]).strip(),
                            station_name=str(row[station_name_col]).strip(),
                            arrival_time=str(row[arrival_col]).strip(),
                            departure_time=str(row[departure_col]).strip(),
                            distance=str(row[distance_col]).strip()
                        )
                    )

                first = rows[0]

                schedules[train_no] = TrainSchedule(
                    train_number=train_no,
                    train_name=str(first[train_name_col]).strip(),
                    source_station=str(first[source_code_col]).strip(),
                    destination_station=str(first[destination_code_col]).strip(),
                    stops=stops
                )

            except Exception:
                continue

        print(f"Skipped invalid rows: {invalid_row_count}")
        print(f"Successfully parsed {len(schedules)} schedules.")

        if invalid_row_count:
            print("\nSkipped rows (non-numeric SEQ):")
            for seq, trains in skipped_values.items():
                affected = sorted(set(trains))
                if len(affected) <= 5:
                    trains_str = ", ".join(affected)
                else:
                    trains_str = ", ".join(affected[:5]) + f" ... (+{len(affected) - 5} more)"
                print(f"  SEQ='{seq}'  trains=[{trains_str}]  count={len(affected)}")

        return schedules