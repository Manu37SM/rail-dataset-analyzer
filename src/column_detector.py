TRAIN_NUMBER_COLUMNS = [
    "train_no",
    "train_number",
    "Train No",
    "Train Number",
    "trainNo"
]

TRAIN_NAME_COLUMNS = [
    "train_name",
    "Train Name",
    "name"
]

SOURCE_COLUMNS = [

    # Old dataset
    "Source Station",

    # New dataset
    "source_station",
    "source_station_code",
    "source",
    "from",
    "from_station"

]

DESTINATION_COLUMNS = [

    # Old dataset
    "Destination Station",

    # New dataset
    "destination_station",
    "destination_station_code",
    "destination",
    "to",
    "to_station"

]

ARRIVAL_COLUMNS = [

    "Arrival Time",

    "Arrival time",

    "arrival_time",

    "arrival"

]

DEPARTURE_COLUMNS = [

    "Departure Time",

    "Departure time",

    "departure_time",

    "departure"

]

SEQ_COLUMNS = [

    "SEQ",

    "Seq",

    "Sequence"

]

STATION_CODE_COLUMNS = [

    "Station Code",

    "station_code"

]

STATION_NAME_COLUMNS = [

    "Station Name",

    "station_name"

]

DISTANCE_COLUMNS = [

    "Distance",

    "distance"

]

SOURCE_NAME_COLUMNS = [

    "Source Station Name",

    "source_station_name"

]

DESTINATION_NAME_COLUMNS = [

    "Destination Station Name",

    "destination_station_name"

]

CLASSES_COLUMNS = [

    "classes",

    "Classes",

    "class_code",

    "train_classes"

]

RUNNING_DAYS_COLUMNS = [

    # New dataset
    "days_of_week",
    "running_days",
    "Running Days",
    "days",
    "running_days_desc"

]


def find_column(df, candidates):

    for column in candidates:
        if column in df.columns:
            return column

    return None