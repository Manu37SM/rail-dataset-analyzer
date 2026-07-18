from schedule_parser import ScheduleParser
from old_schedule_parser import OldScheduleParser
from schedule_comparator import ScheduleComparator
from migration_builder import MigrationBuilder
from station_resolver import StationResolver
from migration_report import MigrationReport


class MigrationEngine:

    def __init__(self, station_master):

        self.resolver = StationResolver(station_master)

        self.old_parser = OldScheduleParser()

        self.new_parser = ScheduleParser(
            self.resolver
        )

        self.comparator = ScheduleComparator()

        self.builder = MigrationBuilder()

    def migrate(
        self,
        old_df,
        new_df
    ):

        report = MigrationReport()

        print("Parsing old dataset...")

        old_schedules = self.old_parser.parse(
            old_df
        )

        print(f"{len(old_schedules)} schedules loaded.")

        print()

        print("Parsing new dataset...")

        new_schedules = self.new_parser.parse(
            new_df
        )

        print(f"{len(new_schedules)} schedules loaded.")

        print()

        import_rows = []

        stats = {

            "new": 0,

            "updated": 0,

            "unchanged": 0,

            "missing": 0

        }

        #
        # Compare every train
        #

        for train_no, new_schedule in new_schedules.items():

            #
            # New train
            #

            if train_no not in old_schedules:

                stats["new"] += 1

                report.add_new(
                    train_no
                )

                import_rows.extend(

                    self.builder.build(
                        new_schedule
                    )

                )

                continue

            #
            # Existing train
            #

            difference = self.comparator.compare(

                old_schedules[train_no],

                new_schedule

            )

            if difference.is_changed:

                stats["updated"] += 1

                report.add_updated(

                    train_no,

                    difference.changes

                )

                import_rows.extend(

                    self.builder.build(
                        new_schedule
                    )

                )

            else:

                stats["unchanged"] += 1

        #
        # Missing trains
        #

        for train_no in old_schedules:

            if train_no not in new_schedules:

                stats["missing"] += 1

                report.add_missing(
                    train_no
                )
        
        report.export()

        return import_rows, stats