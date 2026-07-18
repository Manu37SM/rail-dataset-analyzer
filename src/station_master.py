import pandas as pd


def load_station_master(path="input/station_master.csv"):

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )

    df.columns = df.columns.str.strip()

    return df