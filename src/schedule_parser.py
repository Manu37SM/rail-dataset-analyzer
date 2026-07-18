from column_detector import (
    find_column,
    TRAIN_NUMBER_COLUMNS,
    TRAIN_NAME_COLUMNS,
    SOURCE_COLUMNS,
    DESTINATION_COLUMNS,
    CLASSES_COLUMNS,
    RUNNING_DAYS_COLUMNS,
)

from models import ScheduleStop
from models import TrainSchedule
import pandas as pd


class ScheduleParser:

    def __init__(self, resolver):
        self.resolver = resolver
        self.cache = {}

        # Collect stations that couldn't be resolved
        self.unresolved_stations = set()

    # ----------------------------------------------------------

    # Known control prefixes that appear before station names
    # in the new dataset (RL=Relief, PQ=Parking/Platform Query,
    # RS=Reserved)
    STATION_PREFIXES = {"RL", "PQ", "RS"}

    def _strip_prefix(self, station_name):
        """
        Strip known control prefixes from station names.
        E.g. 'RL Ratnagiri' -> 'Ratnagiri'
        """
        name = station_name.strip()
        parts = name.split(" ", 1)
        if len(parts) == 2 and parts[0] in self.STATION_PREFIXES:
            return parts[1].strip()
        return name

    # ----------------------------------------------------------

    def resolve_station(self, station_name):
        """
        Resolve a station only once.
        Subsequent lookups come from cache.
        Strips control prefixes before resolution.
        """

        station_name = str(station_name).strip()

        # Strip known control prefixes (RL, PQ, RS)
        station_name = self._strip_prefix(station_name)

        if station_name not in self.cache:
            self.cache[station_name] = self.resolver.resolve(station_name)

        return self.cache[station_name]

    # ----------------------------------------------------------

    def parse(self, dataframe):

        train_col = find_column(dataframe, TRAIN_NUMBER_COLUMNS)
        name_col = find_column(dataframe, TRAIN_NAME_COLUMNS)
        source_col = find_column(dataframe, SOURCE_COLUMNS)
        dest_col = find_column(dataframe, DESTINATION_COLUMNS)
        classes_col = find_column(dataframe, CLASSES_COLUMNS)
        running_days_col = find_column(dataframe, RUNNING_DAYS_COLUMNS)

        if not all([train_col, name_col, source_col, dest_col]):
            raise Exception("Unable to detect required columns.")

        total = len(dataframe)

        print(f"Total trains to parse: {total}")
        print()

        schedules = {}

        for index, (_, row) in enumerate(dataframe.iterrows(), start=1):

            #
            # Progress
            #
            if index % 100 == 0 or index == total:

                percent = (index / total) * 100

                print(
                    f"Processed {index}/{total} "
                    f"({percent:.1f}%)"
                )

            train_no = str(row[train_col]).strip()

            train_name = str(row[name_col]).strip()

            source_name = str(row[source_col]).strip()

            # For duplicate comparison with intermediate stops, use stripped names
            source_name_raw = source_name
            source_name_stripped = self._strip_prefix(source_name)

            destination_name = str(row[dest_col]).strip()

            destination_name_stripped = self._strip_prefix(destination_name)

            departure = str(row["departure_time"]).strip()

            arrival = str(row["arrival_time"]).strip()

            #
            # Optional per-train attributes
            #

            classes = str(row[classes_col]).strip() if classes_col else ""

            running_days = (
                str(row[running_days_col]).strip()
                if running_days_col else ""
            )

            #
            # Cached station resolution
            #

            source = self.resolve_station(source_name)

            if not source.station_code:

                self.unresolved_stations.add(source_name)

                source.station_code = "UNKNOWN"
                source.canonical_name = source_name

            destination = self.resolve_station(destination_name)

            if not destination.station_code:

                self.unresolved_stations.add(destination_name)

                destination.station_code = "UNKNOWN"
                destination.canonical_name = destination_name

            stops = []

            sequence = 1

            #
            # Source
            #

            stops.append(

                ScheduleStop(

                    sequence=sequence,

                    station_code=source.station_code,

                    station_name=source.canonical_name,

                    arrival_time="",

                    departure_time=departure,

                    distance=""

                )

            )

            sequence += 1

            #
            # Intermediate Stops
            #

            intermediate = str(
                row.get("intermediate_stops", "")
            ).strip()

            if intermediate:

                for stop in intermediate.split("|"):

                    stop = stop.strip()

                    if not stop:
                        continue

                    idx = stop.find("(")

                    if idx == -1:
                        continue

                    station_name = stop[:idx].strip()

                    #
                    # Skip duplicate source and destination stations
                    #

                    if station_name.strip().lower() == source_name_stripped.strip().lower():
                        continue

                    if station_name.strip().lower() == destination_name_stripped.strip().lower():
                        continue

                    values = stop[idx + 1:-1]

                    arrival_time = ""

                    departure_time = ""

                    for part in values.split(","):

                        part = part.strip()

                        if "=" not in part:
                            continue

                        key, value = part.split("=", 1)

                        key = key.strip()

                        value = value.strip()

                        if key == "arr":
                            arrival_time = value

                        elif key == "dep":
                            departure_time = value

                    resolved = self.resolve_station(station_name)

                    #
                    # If station couldn't be resolved,
                    # preserve original station name.
                    #

                    station_code = resolved.station_code
                    station_display = resolved.canonical_name

                    if not station_code:

                        self.unresolved_stations.add(station_name)

                        station_code = "UNKNOWN"
                        station_display = station_name

                    stops.append(

                        ScheduleStop(

                            sequence=sequence,

                            station_code=station_code,

                            station_name=station_display,

                            arrival_time=arrival_time,

                            departure_time=departure_time,

                            distance=""

                        )

                    )

                    sequence += 1

            #
            # Destination
            #

            stops.append(

                ScheduleStop(

                    sequence=sequence,

                    station_code=destination.station_code,

                    station_name=destination.canonical_name,

                    arrival_time=arrival,

                    departure_time="",

                    distance=str(
                        row["distance"]
                    ).strip()

                )

            )

            schedules[train_no] = TrainSchedule(

                train_number=train_no,

                train_name=train_name,

                source_station=source.station_code,

                destination_station=destination.station_code,

                stops=stops,

                classes=classes,

                running_days=running_days

            )

        print()
        print("=" * 60)
        print("Parsing Complete")
        print("=" * 60)
        print(f"Schedules Built : {len(schedules)}")
        print(f"Unique Stations Cached : {len(self.cache)}")
        print("=" * 60)

        # --------------------------------------------------

        if self.unresolved_stations:

            pd.DataFrame(

                sorted(self.unresolved_stations),

                columns=["Station"]

            ).to_csv(

                "reports/unresolved_stations.csv",

                index=False

            )

            print(
                f"Generated reports/unresolved_stations.csv "
                f"({len(self.unresolved_stations)} stations)"
            )

        # --------------------------------------------------

        return schedules