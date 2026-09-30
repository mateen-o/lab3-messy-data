\# Lab 3: Parsing Messy Health and Genomic Data



PUBH 6854. This lab compares regex-based and AI-assisted cleaning of two synthetic messy files:

`messy\_samples.csv` (60 clinical records) and `messy\_sequences.fasta` (8 DNA sequences).



\- \*\*Write-up\*\* (comparison, failure modes, analytic readiness): \[writeup.md](writeup.md)

\- \*\*AI prompts and usage:\*\* \[AI\_USAGE.md](AI\_USAGE.md)



\## Setup



```

conda env create -f environment.yml

conda activate pubh6854-lab3

```



\## How to run (from the repo root)



| Step | Command | Input | Output |

|---|---|---|---|

| Regex: samples | `python scripts/clean\_samples.py data/raw/messy\_samples.csv output/regex\_samples\_clean.csv` | raw CSV | cleaned table, one row per sample, with a `parse\_notes` column recording every assumption |

| Regex: FASTA | `python scripts/clean\_fasta.py data/raw/messy\_sequences.fasta output/regex\_sequences\_clean.csv` | raw FASTA | one row per sequence, header fields split into columns, plus actual length and GC content |

| Compare: samples | `python scripts/compare.py output/regex\_samples\_clean.csv output/ai\_samples\_clean\_isodates.csv sample\_id output/compare\_samples.csv` | regex + AI tables | every cell where the two methods disagree |

| Compare: FASTA | `python scripts/compare.py output/regex\_sequences\_clean.csv output/ai\_sequences\_clean.csv sample\_id output/compare\_sequences.csv` | regex + AI tables | every cell where the two methods disagree |

| Grad addendum | `python scripts/build\_analytic\_table.py output/regex\_samples\_clean.csv output/analytic\_table.csv` | cleaned samples | samples × features × metadata table, plus a readiness report printed to the console |



\## Repository layout



```

data/raw/        raw input files (unchanged)

scripts/         cleaning, comparison and analytic-table scripts

output/          all generated tables:

&#x20;                  regex\_\*\_clean.csv            regex output

&#x20;                  ai\_\*\_clean.csv               AI output, exactly as returned

&#x20;                  ai\_samples\_clean\_isodates.csv AI output with dates converted to ISO (for comparison only)

&#x20;                  compare\_\*.csv                cell-level disagreements

&#x20;                  analytic\_table.csv           grad addendum table

```



\## Notes



\- The data is synthetic (no PHI). See the course repo's `SOURCE.md`.

\- Don't open and save the output CSVs in Excel: it rewrites ISO dates (`1962-07-09`) as `7/9/1962`.

