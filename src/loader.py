import pandas as pd


def load_dataset(path):

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )

    df.columns = df.columns.str.strip()

    return df