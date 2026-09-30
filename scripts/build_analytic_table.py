"""
Lab 3 - Graduate addendum: samples x features x metadata table.

Usage:
    python scripts/build_analytic_table.py output/regex_samples_clean.csv output/analytic_table.csv

Why this shape (Week 5): a modeling-ready table has
  - ONE row per sample (the unit of analysis),
  - FEATURE columns = numbers a model would actually use,
  - METADATA columns = context (who/where/provenance), kept separate so you
    don't accidentally feed an ID or a free-text note into a model.
We add data-quality FLAG columns rather than dropping problem rows, because
the rubric rewards documenting problems, not hiding them.
"""

import sys

import pandas as pd

ID = "sample_id"

# There is no collection date in this file, so age has to be measured
# against a fixed reference date. We use the dataset's generation date
# (2026-08-08, from SOURCE.md). That choice is itself a readiness issue:
# the real "age at sample collection" is unknown.
AGE_REFERENCE_DATE = pd.Timestamp("2026-08-08")


def main(in_path, out_path):
    df = pd.read_csv(in_path)

    # 1. One row per sample: check for duplicate IDs before trusting the shape.
    #    (s-0003 and S0003 would have been duplicates if IDs weren't normalized.)
    dup = df[ID].duplicated(keep=False)
    print(f"Duplicate sample_ids: {dup.sum()}")

    # 2. Enforce types, so "consistent types" is guaranteed, not hoped for.
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["glucose_mg_dl"] = pd.to_numeric(df["glucose_mg_dl"], errors="coerce")
    for c in ["sex", "site"]:
        df[c] = df[c].astype("category")

    # 3. Features
    df["age_years"] = ((AGE_REFERENCE_DATE - df["dob"]).dt.days / 365.25).round(1)
    features = ["glucose_mg_dl", "age_years"]

    # 4. Data-quality flags (1 = yes). Built from parse_notes so every flag
    #    traces back to a specific parsing decision.
    notes = df["parse_notes"].fillna("")
    df["flag_glucose_asterisk"] = df["glucose_asterisk"].astype(int)
    df["flag_unit_conflict"] = notes.str.contains("UNIT CONFLICT").astype(int)
    df["flag_dob_ambiguous"] = notes.str.contains("AMBIGUOUS").astype(int)
    df["flag_sex_missing"] = (df["sex"] == "Unknown").astype(int)
    df["flag_redraw_requested"] = df["notes"].fillna("").str.contains("re-draw").astype(int)
    flags = [c for c in df.columns if c.startswith("flag_")]

    # 5. Metadata. patient_name is deliberately LEFT OUT: it's a direct
    #    identifier, not an analytic variable, and doesn't belong in a
    #    table meant for modeling.
    metadata = ["sex", "site", "dob", "glucose_unit_original", "notes"]

    table = df[[ID] + features + flags + metadata].set_index(ID)
    table.to_csv(out_path)

    # 6. Readiness report - copy these numbers into your write-up.
    print(f"Analytic table: {table.shape[0]} samples x {len(features)} features "
          f"x {len(flags)} quality flags x {len(metadata)} metadata -> {out_path}\n")
    print("Column types:")
    print(table[features + metadata].dtypes.to_string(), "\n")
    print("Missing values per column:")
    print(table[features + metadata].isna().sum().to_string(), "\n")
    print("Quality flags (number of samples):")
    print(table[flags].sum().to_string(), "\n")
    print(f"Samples with at least one flag: {(table[flags].sum(axis=1) > 0).sum()} of {len(table)}\n")
    print("Feature summary:")
    print(table[features].describe().round(1).to_string(), "\n")
    print("Glucose by unit as written (are the 'mmol/L' rows really different?):")
    print(table.groupby("glucose_unit_original")["glucose_mg_dl"].describe().round(1).to_string())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/build_analytic_table.py <clean_samples_csv> <output_csv>")
    main(*sys.argv[1:])
