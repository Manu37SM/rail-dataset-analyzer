from dataclasses import dataclass

from models import TrainSchedule


@dataclass
class ScheduleDifference:

    train_number: str

    is_changed: bool

    changes: list[str]


class ScheduleComparator:

    def compare(
        self,
        old_schedule: TrainSchedule,
        new_schedule: TrainSchedule
    ):

        changes = []

        #
        # Metadata
        #

        if old_schedule.train_name != new_schedule.train_name:
            changes.append("TRAIN_NAME")

        if old_schedule.source_station != new_schedule.source_station:
            changes.append("SOURCE")

        if old_schedule.destination_station != new_schedule.destination_station:
            changes.append("DESTINATION")

        #
        # Number of Stops
        #

        if len(old_schedule.stops) != len(new_schedule.stops):

            changes.append("STOP_COUNT")

        #
        # Compare stops
        #

        min_length = min(

            len(old_schedule.stops),

            len(new_schedule.stops)

        )

        for i in range(min_length):

            old_stop = old_schedule.stops[i]
            new_stop = new_schedule.stops[i]

            if old_stop.station_code != new_stop.station_code:

                if "ROUTE" not in changes:
                    changes.append("ROUTE")

            if old_stop.arrival_time != new_stop.arrival_time:

                if "ARRIVAL" not in changes:
                    changes.append("ARRIVAL")

            if old_stop.departure_time != new_stop.departure_time:

                if "DEPARTURE" not in changes:
                    changes.append("DEPARTURE")

            #
            # Distance comparison
            #

            if (
                old_stop.distance
                and
                new_stop.distance
                and
                old_stop.distance != new_stop.distance
            ):

                if "DISTANCE" not in changes:
                    changes.append("DISTANCE")

        return ScheduleDifference(

            train_number=new_schedule.train_number,

            is_changed=len(changes) > 0,

            changes=changes

        )