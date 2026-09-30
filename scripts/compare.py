"""
Lab 3 - Task 3: compare the regex output with the AI output, field by field.

Usage:
    python scripts/compare.py output/regex_samples_clean.csv output/ai_samples_clean.csv sample_id output/compare_samples.csv
    python scripts/compare.py output/regex_sequences_clean.csv output/ai_sequences_clean.csv raw_header output/compare_sequences.csv

Why: the rubric wants comparisons that cite SPECIFIC records ("row 14's
date..."). Eyeballing two tables misses things; this lists every single
cell where the two approaches disagree, so you can quote them directly.
"""

import sys

import pandas as pd


def norm(v):
    # Treat "", NaN, "NA" as the same thing, and 70 vs 70.0 as the same
    # number, so we only report REAL disagreements.
    if pd.isna(v) or str(v).strip().lower() in {"", "na", "nan", "none", "null"}:
        return ""
    try:
        return f"{float(v):.2f}"
    except ValueError:
        return str(v).strip().lower()


def main(regex_path, ai_path, key, out_path):
    rx = pd.read_csv(regex_path, dtype=str)
    ai = pd.read_csv(ai_path, dtype=str)

    # Only compare columns both tables have (skip notes / helper columns).
    skip = {key, "parse_notes", "header_style", "sequence", "raw_header", "glucose_asterisk"}
    helper = lambda c: c in skip or c.endswith("_unit_original") or c == "gc_content"
    shared = [c for c in rx.columns if c in ai.columns and not helper(c)]
    missing = [c for c in rx.columns if c not in ai.columns and not helper(c)]
    if missing:
        print(f"WARNING: AI table lacks columns {missing} - ask the AI to include them.")

    merged = rx.merge(ai, on=key, how="outer", suffixes=("_regex", "_ai"), indicator=True)
    only = merged[merged["_merge"] != "both"]
    if len(only):
        print(f"{len(only)} records appear in only one table:")
        print(only[[key, "_merge"]].to_string(index=False))

    diffs = []
    both = merged[merged["_merge"] == "both"]
    for _, r in both.iterrows():
        for c in shared:
            a, b = r[f"{c}_regex"], r[f"{c}_ai"]
            if norm(a) != norm(b):
                diffs.append({key: r[key], "field": c, "regex_value": a, "ai_value": b,
                              "regex_notes": r.get("parse_notes_regex", r.get("parse_notes", ""))})

    out = pd.DataFrame(diffs, columns=[key, "field", "regex_value", "ai_value", "regex_notes"])
    out.to_csv(out_path, index=False)

    total = len(both) * len(shared)
    print(f"\nCompared {len(both)} records x {len(shared)} fields = {total} cells")
    print(f"Agreed: {total - len(out)}  ({(total - len(out)) / max(total, 1):.1%})")
    print(f"Disagreed: {len(out)}  -> details in {out_path}")
    if len(out):
        print("\nDisagreements by field:")
        print(out["field"].value_counts().to_string())


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("usage: python scripts/compare.py <regex_csv> <ai_csv> <key_column> <output_csv>")
    main(*sys.argv[1:])
