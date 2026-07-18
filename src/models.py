from dataclasses import dataclass
from dataclasses import field


@dataclass
class TrainRecord:
    train_number: str
    train_name: str

    source_station_code: str
    source_station_name: str

    destination_station_code: str
    destination_station_name: str

    departure_time: str
    arrival_time: str

    distance: str

    classes: str
    running_days: str


@dataclass
class StationMatch:
    matched: bool

    station_code: str = ""
    canonical_name: str = ""

    method: str = ""
    confidence: float = 0.0

    suggestions: list | None = None

@dataclass
class ScheduleStop:

    sequence: int

    station_name: str
    station_code: str

    arrival_time: str
    departure_time: str

    distance: str = ""


@dataclass
class TrainSchedule:

    train_number: str

    train_name: str

    source_station: str

    destination_station: str

    stops: list[ScheduleStop] = field(default_factory=list)

    classes: str = ""

    running_days: str = ""

@dataclass
class Station:

    code: str

    canonical_name: str

    normalized_name: str

    aliases: list[str]