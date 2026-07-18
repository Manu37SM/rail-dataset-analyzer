import json
import os

import pandas as pd


class DatasetExporter:

    def __init__(self, output_dir="output"):

        self.output_dir = output_dir

        os.makedirs(
            output_dir,
            exist_ok=True
        )

    def export_import_dataset(
        self,
        rows,
        filename="import_ready.csv"
    ):

        df = pd.DataFrame(rows)

        path = os.path.join(
            self.output_dir,
            filename
        )

        df.to_csv(
            path,
            index=False
        )

        print(f"Generated: {path}")

        return df

    def export_train_list(
        self,
        train_numbers,
        filename
    ):

        df = pd.DataFrame({

            "Train Number": sorted(train_numbers)

        })

        path = os.path.join(
            self.output_dir,
            filename
        )

        df.to_csv(
            path,
            index=False
        )

        print(f"Generated: {path}")

    def export_summary(
        self,
        stats
    ):

        path = os.path.join(
            self.output_dir,
            "migration_summary.json"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                stats,

                f,

                indent=4

            )

        print(f"Generated: {path}")