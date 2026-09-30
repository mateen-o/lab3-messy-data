# Lab 3 Write-up: Regex vs. AI-Assisted Cleaning of Messy Health and Genomic Data

**Files:** `messy_samples.csv` (60 clinical records) and `messy_sequences.fasta` (8 DNA sequences)
**Tools:** Python 3.11 / pandas (regex); [TODO: AI tool name, e.g. Claude or ChatGPT] (AI-assisted)

## 1. Approach

**Regex.** `scripts/clean_samples.py` parses each field with its own function and
writes every assumption it makes to a `parse_notes` column, so no change is made
silently. It standardizes IDs (`s-0003` → `S0003`), dates of birth (four formats →
`YYYY-MM-DD`), sex (nine spellings → `M`/`F`/`Unknown`), site (seven spellings →
`Site A/B/C`) and glucose units (→ mg/dL). `scripts/clean_fasta.py` doesn't use one
pattern per header layout, since that would only memorize these eight lines.
Instead it (1) takes the first token as the ID, (2) extracts any `key=value` or
`key:value` pairs, mapping synonyms such as `species`→organism and `target`→gene,
and (3) classifies the remaining fields by what they look like (species name,
gene symbol, "130 bp").

## 2. Comparison

**Agreement.** After converting the AI's dates from M/D/YYYY to ISO format, the two
methods agreed on **347 of 360 values (96.4%)** for the samples file and **40 of 40
(100%)** for the FASTA file. They made the same choices on the hard cases: both read
S0003's `11.24.53` as 1953-11-24 (month-first, 20th century), both read S0017's
`07.16.15` as 2015, and both handled the non-standard FASTA headers sample_004
(`target=BRCA1`, `H.sapiens`) and sample_006 (`seq6|Hsapiens`).

**Disagreement.** All 13 disagreements were glucose values, on the 13 records
labelled mmol/L. The AI multiplied each by 18.016 as instructed, producing values
from 1,855.65 (S0015) to 4,345.46 mg/dL (S0039); S0006 went from 159.9 to 2,880.76.
The regex kept the original values (103.0–241.2) and flagged them as unit conflicts
(see Failure mode 1).

**Date format.** 
*Option A:* The AI returned all 60 dates as M/D/YYYY despite the prompt asking for
YYYY-MM-DD, so its output needed an extra conversion step before it could be compared
or joined. The values themselves were correct.

**Edge cases.** The regex caught three problems the AI output didn't surface:
the impossible glucose values, the 12 ambiguous dates (flagged "AMBIGUOUS: assumed
MM/DD"), and the two FASTA headers whose stated length doesn't match the sequence
(sample_003: 150 vs 157 bp; sample_005: 130 vs 144 bp). [TODO: if the AI mentioned
any of these in its reply, say so here.] The AI's strength was coverage without
setup: it handled all seven site spellings, all eight header layouts and the
key-name synonyms from one prompt, with no rules written in advance.

**Time and effort.** The regex scripts took a long time, including two
rounds of fixes after inspecting the data (the dotted-date format and the glucose
units). The AI took about 35 minutes total to get output, plus time to
fix the file format so it could be compared and to check its values. The AI was
faster to a first answer; the regex was faster to an answer I could trust, because
every decision is written down and reproducible.

## 3. Failures

\### 1. Mislabelled glucose units (AI wrong): S0006, S0039 and 11 others

\*\*What happened:\*\* 13 records have glucose\_unit = "mmol/L", but their values
(103.0–241.2) are in the normal mg/dL range. The AI followed the prompt and
multiplied by 18.016, giving values from 1,855.65 mg/dL (S0015) to
4,345.46 mg/dL (S0039). For example, S0006 went from 159.9 to 2,880.76.
Values this high are not compatible with life.

\*\*Why it failed:\*\* The AI applied the conversion rule without checking whether
the result made sense. The unit label and the size of the number contradict
each other, and only domain knowledge (normal glucose is about 70–140 mg/dL,
or 4–8 mmol/L) shows which one is wrong. The regex kept the original values and
flagged a "unit conflict", but only because I added a plausibility check after
looking at the data. A regex that trusted the label would have made the same
mistake.

\### 2. Dotted dates (regex wrong on the first attempt): S0003 "11.24.53"

\*\*What happened:\*\* My first version of the regex assumed dotted dates were
European (DD.MM.YY), which is common. That reads "11.24.53" as month 24, an
invalid date. The file actually uses month-first dots, which you can only tell
from other rows (06.30.99 and 04.15.95 can't be day-first). Also, Python's
standard two-digit-year rule turns "53" into 2053, a birth date in the future.

\*\*Why it failed:\*\* The format can't be worked out from a single value. It has to
be inferred from the whole column. A regex encodes whatever assumption the
programmer brings to it, so it's only as good as the programmer's first look at
the data. After the fix, both methods read S0003 as 1953-11-24.

\### 3. Ambiguous dates (both methods, unresolvable): S0011 "07.09.61"

\*\*What happened:\*\* 12 dates, such as S0011 "07.09.61" and S0014 "09.12.58", are
valid either way: July 9 or September 7. Both methods chose month-first and
agreed on all 12.

\*\*Why it's a failure mode:\*\* The information isn't in the data. Their agreement
reflects a shared assumption, not a verified answer. The regex at least records
"AMBIGUOUS: assumed MM/DD" for each of these rows; the AI output gives no sign
that any of these dates were uncertain.

\### 4. Header length vs actual sequence (both methods reported it; only regex flagged it): sample\_003, sample\_005

\*\*What happened:\*\* sample\_003's header says length=150bp, but the sequence has
157 bases; sample\_005 says 130 bp but has 144. Both methods reported the
header's numbers and agreed 100%.

\*\*Why it's a failure mode:\*\* The header metadata contradicts the data. A parser
that only reads headers passes the wrong length along with no warning. The regex
counts the bases and flags "LENGTH MISMATCH"; \[the AI did / did not mention the
mismatch].

## 4. Which approach I would trust for a real dataset

For a real dataset I would trust the **regex approach**, used together with the AI
rather than replaced by it. The regex gives the same answer every run, never
invents values, and records every assumption so another person can check it. The
AI was fast and handled messy variants well. The AI is useful as a first pass, to spot
formats I hadn't anticipated or to draft patterns, but its output needs to be
checked against rules and domain knowledge before anyone analyzes it. Neither
method replaces actually looking at the data: both of my regex fixes came from
inspecting the file, not from the code.

## 5. Graduate addendum: samples × features × metadata table

I reshaped the cleaned `messy_samples.csv` output into `output/analytic_table.csv`:
one row per sample (60 rows, no duplicate IDs after normalizing `s-0003`-style IDs).

| Part | Columns |
|---|---|
| Row | one per `sample_id` |
| Features | `glucose_mg_dl`, `age_years` (from DOB) |
| Quality flags (1/0) | `flag_glucose_asterisk` (2), `flag_unit_conflict` (13), `flag_dob_ambiguous` (12), `flag_sex_missing` (18), `flag_redraw_requested` (4) |
| Metadata | `sex`, `site`, `dob`, `glucose_unit_original`, `notes` |
| Excluded | `patient_name`: a direct identifier, not an analytic variable |

| sample_id | glucose_mg_dl | age_years | flag_unit_conflict | flag_dob_ambiguous | flag_glucose_asterisk | sex | site |
|---|---|---|---|---|---|---|---|
| S0001 | 145.9 | 64.1 | 0 | 1 | 0 | F | Site B |
| S0006 | 159.9 | 57.7 | 1 | 0 | 0 | F | Site C |
| S0012 | 110.4 | 30.2 | 0 | 1 | 0 | Unknown | Site A |
| S0039 | 241.2 | 46.3 | 1 | 1 | 1 | M | Site C |
| S0042 | 209.0 | 20.3 | 0 | 0 | 1 | F | Site C |

Problems are flagged rather than dropped: 35 of 60 samples carry at least one flag.

**Analytic readiness.** Types are consistent and every sample is kept, but the
table isn't modeling-ready. The 13 "mmol/L" glucose values are kept as mg/dL on the
evidence of their magnitude, and that needs confirming against a data dictionary
before any glucose analysis. The file has no collection date, so age is measured
against a fixed reference date (2026-08-08), and 12 birth dates are ambiguous, so
age is approximate. Decisions are still needed on the 18 samples with unknown sex
(5 blank and 13 recorded as unknown, which may mean different things), on whether
the 4 "re-draw requested" and 2 asterisked glucose values are usable, and on the 7
participants under 18, who may need different glucose reference ranges.
