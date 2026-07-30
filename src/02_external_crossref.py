#!/usr/bin/env python3
"""
02_external_crossref.py
========================
Cross-references the RailLens dataset against publicly available BULK
reference datasets that could actually be fetched programmatically in this
environment.

IMPORTANT SOURCE-QUALITY DISCLOSURE (read before trusting these results):
  - We attempted to reach data.gov.in (Ministry of Railways OGD catalog),
    which is the closest thing to an "official" bulk source. As of this run,
    its Railway Station catalog page returns "No Result Found" for
    downloadable resources without an authenticated login, and the portal
    itself displays a banner stating it is "a sandbox environment created
    for testing and demonstration purposes only... may be incomplete or
    inaccurate." It could not be used for bulk verification.
  - NTES (enquiry.indianrail.gov.in) and CRIS do not publish a bulk/download
    dataset -- they are live lookup systems queried one train/station at a
    time, which is not feasible to do exhaustively for 11,113 trains and
    8,151 stations in this environment.
  - The datasets actually used below (datameet/railways, and a secondary
    station-code list) are COMMUNITY-COMPILED / CROWDSOURCED datasets
    (originally scraped from Indian Railways sources around 2015-2016), NOT
    official Ministry of Railways / CRIS publications. They are the same
    tier of source the user's own RailLens project already uses as a
    secondary reference. Treat every "verified" result below as "consistent
    with a community-maintained reference dataset", not as a government
    certification. Anything that disagrees is flagged for manual
    verification against NTES/CRIS by a human, not auto-corrected.

Outputs:
  - data/output/station_crossref.csv   (per unique station code, match status)
  - data/output/train_crossref.csv     (per unique train number, match status)
  - data/output/external_crossref_summary.json
"""
import pandas as pd
import json
import re

IN_PATH = "/home/claude/raillens_validation/data/train_dataset_original.csv"
STATIONS_REF = "/home/claude/raillens_validation/data/reference/stations_datameet.json"
TRAINS_REF = "/home/claude/raillens_validation/data/reference/trains_datameet.json"
SECONDARY_CODES_REF = "/home/claude/raillens_validation/data/reference/station_codes_secondary.json"

STATION_OUT = "/home/claude/raillens_validation/data/output/station_crossref.csv"
TRAIN_OUT = "/home/claude/raillens_validation/data/output/train_crossref.csv"
SUMMARY_OUT = "/home/claude/raillens_validation/data/output/external_crossref_summary.json"


def norm_name(s):
    if not isinstance(s, str):
        return ""
    s = s.upper().strip()
    s = re.sub(r"[.\-]", "", s)
    s = re.sub(r"\bJN\b|\bJUNCTION\b", "JN", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


TRUNCATION_LEN = 12  # the dataset's "Station Name" column is hard-truncated at 12 chars
                      # (confirmed: max observed length across all 186,124 rows == 12,
                      # with 51,145 rows / 27.5% sitting exactly at that cap)


def is_truncation_consistent(dataset_name, reference_name):
    """True if dataset_name looks like reference_name truncated to TRUNCATION_LEN chars."""
    if not dataset_name or not reference_name:
        return False
    if len(dataset_name) < TRUNCATION_LEN:
        return False  # not at the truncation boundary, so this isn't a truncation case
    n_ref = norm_name(reference_name)
    n_ds = norm_name(dataset_name)
    return n_ref.startswith(n_ds) or reference_name.upper().startswith(dataset_name.upper())


def main():
    df = pd.read_csv(IN_PATH, dtype=str, keep_default_na=False, na_values=[""])

    # ---- Load reference datasets ----
    with open(STATIONS_REF) as f:
        stations_geo = json.load(f)
    station_ref = {}
    for feat in stations_geo["features"]:
        p = feat["properties"]
        code = p.get("code")
        if code:
            station_ref[code] = {
                "name": p.get("name"),
                "state": p.get("state"),
                "zone": p.get("zone"),
            }

    with open(TRAINS_REF) as f:
        trains_geo = json.load(f)
    train_ref = {}
    for feat in trains_geo["features"]:
        p = feat["properties"]
        num = p.get("number")
        if num:
            train_ref[str(num).lstrip("0") or "0"] = {
                "name": p.get("name"),
                "zone": p.get("zone"),
                "from_code": p.get("from_station_code"),
                "from_name": p.get("from_station_name"),
                "to_code": p.get("to_station_code"),
                "to_name": p.get("to_station_name"),
                "type": p.get("type"),
            }

    with open(SECONDARY_CODES_REF) as f:
        secondary_list = json.load(f)
    secondary_name_to_code = secondary_list[0] if secondary_list else {}
    secondary_code_to_names = {}
    for name, code in secondary_name_to_code.items():
        secondary_code_to_names.setdefault(code, set()).add(name)

    # ================= STATION CROSS-REFERENCE =================
    station_rows = []
    unique_stations = df[["Station Code", "Station Name"]].drop_duplicates(subset=["Station Code"])
    for _, row in unique_stations.iterrows():
        code = row["Station Code"]
        name = row["Station Name"]
        rec = {"station_code": code, "station_name_in_dataset": name}

        ref = station_ref.get(code)
        if ref is not None:
            rec["found_in_datameet_reference"] = True
            rec["datameet_name"] = ref["name"]
            rec["datameet_state"] = ref["state"]
            rec["datameet_zone"] = ref["zone"]
            name_match = norm_name(name) == norm_name(ref["name"]) if ref["name"] else None
            rec["name_match"] = name_match
            if name_match:
                rec["status"] = "VERIFIED"
                rec["suggested_full_name"] = None
            elif ref["name"] and is_truncation_consistent(name, ref["name"]):
                rec["status"] = "VERIFIED_TRUNCATED_IN_SOURCE"
                rec["suggested_full_name"] = ref["name"]
            else:
                rec["status"] = "NAME_MISMATCH_REQUIRES_MANUAL_VERIFICATION"
                rec["suggested_full_name"] = ref["name"]
        else:
            rec["found_in_datameet_reference"] = False
            rec["datameet_name"] = None
            rec["datameet_state"] = None
            rec["datameet_zone"] = None
            rec["name_match"] = None
            # try secondary source (name -> code dictionary) as a second attempt
            if code in secondary_code_to_names:
                rec["found_in_secondary_reference"] = True
                rec["secondary_names_for_code"] = "; ".join(sorted(secondary_code_to_names[code]))
                n1 = norm_name(name)
                match2 = any(n1 == norm_name(n2) or n1 in norm_name(n2) or norm_name(n2) in n1
                             for n2 in secondary_code_to_names[code])
                rec["status"] = "VERIFIED_SECONDARY_SOURCE_ONLY" if match2 else "REQUIRES_MANUAL_VERIFICATION"
            else:
                rec["found_in_secondary_reference"] = False
                rec["status"] = "NOT_FOUND_IN_ANY_REFERENCE_REQUIRES_MANUAL_VERIFICATION"

        station_rows.append(rec)

    station_df = pd.DataFrame(station_rows)
    station_df.to_csv(STATION_OUT, index=False)

    # ================= TRAIN CROSS-REFERENCE =================
    train_rows = []
    unique_trains = df[["Train No", "Train Name"]].drop_duplicates(subset=["Train No"])
    for _, row in unique_trains.iterrows():
        tno = row["Train No"]
        tname = row["Train Name"]
        rec = {"train_no": tno, "train_name_in_dataset": tname}

        key = str(tno).lstrip("0") or "0" if str(tno).isdigit() else None
        ref = train_ref.get(key) if key else None
        if ref is not None:
            rec["found_in_datameet_reference"] = True
            rec["datameet_name"] = ref["name"]
            rec["datameet_zone"] = ref["zone"]
            rec["datameet_from"] = ref["from_code"]
            rec["datameet_to"] = ref["to_code"]
            rec["status"] = "VERIFIED_PRESENT"
        else:
            rec["found_in_datameet_reference"] = False
            rec["datameet_name"] = None
            rec["datameet_zone"] = None
            rec["datameet_from"] = None
            rec["datameet_to"] = None
            rec["status"] = "NOT_IN_2016_REFERENCE_MAY_BE_NEWER_OR_WITHDRAWN_REQUIRES_MANUAL_VERIFICATION"

        train_rows.append(rec)

    train_df = pd.DataFrame(train_rows)
    train_df.to_csv(TRAIN_OUT, index=False)

    # ================= SUMMARY =================
    summary = {
        "reference_datasets_used": [
            {
                "name": "datameet/railways stations.json",
                "url": "https://github.com/datameet/railways/blob/master/stations.json",
                "type": "community-crowdsourced (NOT official CRIS/Ministry of Railways)",
                "record_count": len(station_ref),
            },
            {
                "name": "datameet/railways trains.json",
                "url": "https://github.com/datameet/railways/blob/master/trains.json",
                "type": "community-crowdsourced (NOT official CRIS/Ministry of Railways), circa 2015-2016, train-level metadata only (no per-stop schedule)",
                "record_count": len(train_ref),
            },
            {
                "name": "mayurrawte/IndianRailApi station_codes.json",
                "url": "https://github.com/mayurrawte/IndianRailApi/blob/master/data/station_codes.json",
                "type": "community-compiled secondary station name-to-code list, used only as a fallback when the primary reference has no match",
                "record_count": len(secondary_name_to_code),
            },
        ],
        "sources_attempted_but_unusable": [
            {
                "name": "data.gov.in Railway Station catalog (Ministry of Railways)",
                "url": "https://www.data.gov.in/catalog/railway-station",
                "reason": "No downloadable resources without authenticated login; portal displays a "
                          "'sandbox environment for testing and demonstration only' banner; last "
                          "updated 2015.",
            },
            {
                "name": "NTES (enquiry.indianrail.gov.in)",
                "reason": "Live single-query lookup system, not a bulk/downloadable dataset; "
                          "exhaustively querying 11,113 trains individually was not feasible in this session.",
            },
            {
                "name": "CRIS official bulk datasets",
                "reason": "No public bulk download endpoint identified.",
            },
        ],
        "station_crossref": {
            "total_unique_stations": len(station_df),
            "status_counts": station_df["status"].value_counts().to_dict(),
        },
        "train_crossref": {
            "total_unique_trains": len(train_df),
            "status_counts": train_df["status"].value_counts().to_dict(),
        },
    }
    with open(SUMMARY_OUT, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
