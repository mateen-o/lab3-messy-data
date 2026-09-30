"""
Lab 3 - Task 1 (regex cleaning) for messy_samples.csv

Usage (from the repo root, with the conda env active):
    python scripts/clean_samples.py data/raw/messy_samples.csv output/regex_samples_clean.csv

Raw columns: sample_id, patient_name, dob, sex, enrollment_site,
             glucose_value, glucose_unit, notes

Why this script is built the way it is:
- Every field goes through its own small function, so when a record fails
  you can point to the exact rule that failed (useful for Task 4).
- Nothing is silently dropped or silently "fixed": every assumption the
  script makes is written to a `parse_notes` column for that row.

What is messy in this file, and where each is handled:
  sample_id  "S0001" vs "s-0003" .................. parse_sample_id()
  patient_name  "J. SMITH" vs "J. Smith" ........... parse_name()
  dob  4 formats, incl. 2-digit years .............. parse_dob()
  sex  M/Male/m/F/Female/f/U/unknown/blank ......... parse_sex()
  site  "siteB", "Site  C", "SITE-A", "site_a" ..... parse_site()
  glucose  "241.2*", unit case, mmol/L labels ...... parse_glucose()
"""

import re
import sys
from datetime import date

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Settings (already filled in for this file)
# ---------------------------------------------------------------------------

# Two-digit years: DOBs in this file run from the 1950s to 2015, so a
# 2-digit year at or below this cutoff is 20xx and above it is 19xx.
# e.g. "11.24.53" -> 1953, "07.16.15" -> 2015.
TWO_DIGIT_YEAR_CUTOFF = 26  # the current year, 2026

# Glucose conversion: mg/dL = mmol/L x 18.016 (glucose molar mass / 10).
GLUCOSE_MMOL_TO_MGDL = 18.016
# Physiologically, glucose in mmol/L is roughly 2-35. A value labelled
# "mmol/L" above this is almost certainly a mg/dL value with the wrong label.
MAX_PLAUSIBLE_MMOL = 35

SEX_MAP = {
    "m": "M", "male": "M",
    "f": "F", "female": "F",
    "u": "Unknown", "unknown": "Unknown",
}

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# ---------------------------------------------------------------------------
# 2. Field parsers - each returns (clean value, note)
# ---------------------------------------------------------------------------


def parse_sample_id(raw):
    # "S0001", "s-0003" -> "S0003". Pull out the digits and re-pad to 4, so
    # every ID has exactly one spelling (needed for joins later).
    m = re.fullmatch(r"\s*[sS]\s*[-_]?\s*(\d+)\s*", raw)
    if not m:
        return raw.strip(), f"unrecognized sample_id '{raw}'"
    new = f"S{int(m[1]):04d}"
    return new, ("" if new == raw else f"id '{raw}' -> {new}")


def parse_name(raw):
    # "J. SMITH" -> "J. Smith". Only casing is fixed; we don't try to
    # decide whether two rows with the same name are the same person.
    s = re.sub(r"\s+", " ", raw).strip()
    if not s:
        return None, "name missing"
    return re.sub(r"[A-Za-z]+", lambda w: w[0].capitalize(), s), ""


def _year(y):
    y = int(y)
    if y >= 100:
        return y
    return 2000 + y if y <= TWO_DIGIT_YEAR_CUTOFF else 1900 + y


def parse_dob(raw):
    """Return (ISO date or None, note). Four formats appear in this file."""
    s = raw.strip()
    if not s:
        return None, "dob missing"
    try:
        # 1957-02-27  (ISO - never ambiguous)
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat(), ""

        # 05-Dec-1968  (day-monthname-year - never ambiguous)
        m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})[A-Za-z]*-(\d{2,4})", s)
        if m and m[2].lower() in MONTHS:
            return date(_year(m[3]), MONTHS[m[2].lower()], int(m[1])).isoformat(), ""

        # 07/09/1962 (slashes) and 11.24.53 (dots): both MONTH first.
        # Evidence from the file: dotted dates like 11.24.53, 06.30.99 and
        # 04.15.95 can only be month-first (no month 24/30/15), and no dotted
        # date has a first number above 12. So dots are US order here, NOT
        # the European DD.MM.YY you might expect.
        m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})", s)
        if m:
            mo, d = int(m[1]), int(m[2])
            notes = []
            if len(m[3]) == 2:
                notes.append(f"2-digit year '{m[3]}' -> {_year(m[3])}")
            if d <= 12 and mo != d:
                # Both numbers could be a month, so the order is an assumption.
                notes.append("AMBIGUOUS: assumed MM/DD")
            return date(_year(m[3]), mo, d).isoformat(), "; ".join(notes)
    except ValueError:
        return None, f"impossible date '{s}'"
    return None, f"unrecognized dob '{s}'"


def parse_sex(raw):
    key = raw.strip().lower()
    if key == "":
        # Blank is kept distinct from an explicit "unknown" in the notes,
        # because "not recorded" and "recorded as unknown" aren't the same.
        return "Unknown", "sex blank"
    if key in SEX_MAP:
        return SEX_MAP[key], ""
    return "Unknown", f"unrecognized sex '{raw}'"


def parse_site(raw):
    # "siteB", "Site  C", "Site C ", "SITE-A", "site_a" -> "Site A/B/C".
    # One regex: the word "site", any mix of space/-/_ (or nothing), one letter.
    m = re.fullmatch(r"\s*site[\s_-]*([a-z])\s*", raw, flags=re.IGNORECASE)
    if m:
        return f"Site {m[1].upper()}", ""
    if not raw.strip():
        return None, "site missing"
    return raw.strip(), f"unrecognized site '{raw}'"


def parse_glucose(raw_value, raw_unit):
    """Return (mg/dL value, cleaned unit label, asterisk flag, note)."""
    notes = []
    v = raw_value.strip()

    # Trailing "*" - its meaning isn't documented (flag? re-test?), so we
    # strip it to get the number but keep a 1/0 column saying it was there.
    starred = int(v.endswith("*"))
    v = v.rstrip("*").strip()
    if starred:
        notes.append("trailing * removed")

    if not re.fullmatch(r"\d+(\.\d+)?", v):
        return None, None, starred, f"unparseable glucose '{raw_value}'"
    value = float(v)

    # Unit: "mg/dL", "MG/DL", "mg/dl" are the same unit in different case.
    u = re.sub(r"\s+", "", raw_unit).lower()
    if re.fullmatch(r"mg/?dl", u):
        unit = "mg/dL"
    elif re.fullmatch(r"mmol/?l", u):
        unit = "mmol/L"
    else:
        return None, raw_unit, starred, f"unknown unit '{raw_unit}'"

    if unit == "mmol/L":
        if value > MAX_PLAUSIBLE_MMOL:
            # e.g. 159.9 "mmol/L" would be 2,881 mg/dL - not survivable.
            # The number is already in mg/dL range, so the LABEL is wrong.
            # We keep the value as mg/dL and flag it instead of converting.
            notes.append(f"UNIT CONFLICT: {value} is implausible in mmol/L; kept as mg/dL")
        else:
            value = round(value * GLUCOSE_MMOL_TO_MGDL, 1)
            notes.append("converted mmol/L -> mg/dL")

    return value, unit, starred, "; ".join(notes)


# ---------------------------------------------------------------------------
# 3. Run
# ---------------------------------------------------------------------------

def main(in_path, out_path):
    # dtype=str + keep_default_na=False: read everything as raw text so
    # pandas doesn't convert dates, blanks or "NA" before our regexes run.
    raw = pd.read_csv(in_path, dtype=str, keep_default_na=False)
    print(f"Read {len(raw)} rows, columns: {list(raw.columns)}")

    rows = []
    for _, r in raw.iterrows():
        out, notes = {}, []
        out["sample_id"], n = parse_sample_id(r["sample_id"]); notes.append(n)
        out["patient_name"], n = parse_name(r["patient_name"]); notes.append(n)
        out["dob"], n = parse_dob(r["dob"]); notes.append(n)
        out["sex"], n = parse_sex(r["sex"]); notes.append(n)
        out["site"], n = parse_site(r["enrollment_site"]); notes.append(n)
        (out["glucose_mg_dl"], out["glucose_unit_original"],
         out["glucose_asterisk"], n) = parse_glucose(r["glucose_value"], r["glucose_unit"])
        notes.append(n)
        out["notes"] = r["notes"].strip() or None     # free text, kept as-is
        out["parse_notes"] = "; ".join(x for x in notes if x)
        rows.append(out)

    clean = pd.DataFrame(rows)
    clean.to_csv(out_path, index=False)

    # Self-check: each line should show only ONE spelling per real value.
    print(f"Wrote {len(clean)} rows -> {out_path}\n")
    print("sex:  ", clean["sex"].value_counts(dropna=False).to_dict())
    print("site: ", clean["site"].value_counts(dropna=False).to_dict())
    print("unit as written:", clean["glucose_unit_original"].value_counts().to_dict())
    print("dob not parsed:", clean["dob"].isna().sum())
    print("ambiguous dob (MM/DD assumed):", clean.parse_notes.str.contains("AMBIGUOUS").sum())
    print("unit conflicts (mmol/L label, mg/dL value):",
          clean.parse_notes.str.contains("UNIT CONFLICT").sum())
    print("asterisk values:", clean["glucose_asterisk"].sum())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/clean_samples.py <raw_csv> <output_csv>")
    main(sys.argv[1], sys.argv[2])
