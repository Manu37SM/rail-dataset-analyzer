import re

from column_detector import (
    find_column,
    TRAIN_NUMBER_COLUMNS,
    TRAIN_NAME_COLUMNS,
    SOURCE_COLUMNS,
    DESTINATION_COLUMNS,
)


def value(row, column):

    if column is None:
        return ""

    return str(row[column]).strip()


# Common railway name replacements
REPLACEMENTS = {

    # City renames
    "bombay": "mumbai",
    "madras": "chennai",
    "bangalore": "bengaluru",
    "calcutta": "kolkata",

    # Railway abbreviations
    " jn ": " junction ",
    " jn. ": " junction ",
    " j ": " junction ",

    " cantt ": " cantonment ",
    " cantt. ": " cantonment ",

    " rd ": " road ",
    " rd. ": " road ",

    " hal ": " halt ",

    " t ": " terminus ",

    " intl ": " international ",
}


def normalize_name(name: str) -> str:

    if not name:
        return ""

    name = str(name).lower().strip()

    # Remove punctuation
    name = name.replace(".", " ")
    name = name.replace(",", " ")
    name = name.replace("&", " and ")
    name = name.replace("-", " ")

    # Remove text inside brackets
    name = re.sub(r"\(.*?\)", "", name)

    # Pad so replacements work at word boundaries
    name = f" {name} "

    for old, new in REPLACEMENTS.items():
        name = name.replace(old, new)

    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()