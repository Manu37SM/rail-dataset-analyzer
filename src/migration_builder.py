from models import TrainSchedule


class MigrationBuilder:

    def build(self, schedule: TrainSchedule):

        rows = []

        source = schedule.stops[0]
        destination = schedule.stops[-1]

        for stop in schedule.stops:

            # Convert "First"/"Last" placeholders
            arrival = "" if stop.arrival_time.lower() == "first" else stop.arrival_time
            departure = "" if stop.departure_time.lower() == "last" else stop.departure_time

            rows.append({

                "Train No": schedule.train_number,

                "Train Name": schedule.train_name,

                "SEQ": stop.sequence,

                "Station Code": stop.station_code,

                "Station Name": stop.station_name,

                "Arrival Time": arrival,

                "Departure Time": departure,

                "Distance": stop.distance,

                "Source Station": source.station_code,

                "Source Station Name": source.station_name,

                "Destination Station": destination.station_code,

                "Destination Station Name": destination.station_name,

                "Classes": schedule.classes,

                "Running Days": schedule.running_days
            })

        return rows