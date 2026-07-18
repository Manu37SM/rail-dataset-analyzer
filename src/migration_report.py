import os
import pandas as pd


class MigrationReport:

    def __init__(self):

        self.updated = []

        self.new = []

        self.missing = []

    # ------------------------------------------

    def add_new(self, train_number):

        self.new.append({

            "Train Number": train_number

        })

    # ------------------------------------------

    def add_missing(self, train_number):

        self.missing.append({

            "Train Number": train_number

        })

    # ------------------------------------------

    def add_updated(
        self,
        train_number,
        changes
    ):

        self.updated.append({

            "Train Number": train_number,

            "Changes": ", ".join(changes)

        })

    # ------------------------------------------

    def export(
        self,
        output_dir="output"
    ):

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        pd.DataFrame(
            self.new
        ).to_csv(

            os.path.join(
                output_dir,
                "new_trains.csv"
            ),

            index=False

        )

        pd.DataFrame(
            self.updated
        ).to_csv(

            os.path.join(
                output_dir,
                "updated_trains.csv"
            ),

            index=False

        )

        pd.DataFrame(
            self.missing
        ).to_csv(

            os.path.join(
                output_dir,
                "missing_trains.csv"
            ),

            index=False

        )

        print("Generated migration reports.")