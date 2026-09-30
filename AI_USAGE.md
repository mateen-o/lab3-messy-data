\# AI Usage



\## Task 2: AI-assisted extraction

Tool: OpenAI's ChatGPT, accessed 2026-09-30. Time taken: 32.93 seconds for CSV and 4.23 for Fasta file (timed on an iPhone stopwatch)



\### messy\_samples.csv

Prompt:



Clean this messy clinical sample file. Return ONLY a CSV (no commentary, no code)

with exactly these columns in this order:

sample\_id,patient\_name,dob,sex,site,glucose\_mg\_dl,notes



Rules:

\- sample\_id: format S0001 (4 digits).

\- patient\_name: consistent capitalization, e.g. "J. Smith".

\- dob: YYYY-MM-DD.

\- sex: M, F, or Unknown.

\- site: "Site A", "Site B" or "Site C".

\- glucose\_mg\_dl: a number in mg/dL. Convert mmol/L to mg/dL by multiplying by 18.016.

&#x20; Remove stray annotations such as a trailing "\*".

\- notes: copy as-is; leave empty if empty.

\- Keep all 60 rows, one row per sample.





\### messy\_sequences.fasta

Prompt:

Parse the FASTA headers below. Return ONLY a CSV with these columns:

sample\_id,organism,gene,stated\_length,note,actual\_length



\- sample\_id: format sample\_001 (3 digits), based on the number in the header ID.

\- organism: full species name, e.g. "Homo sapiens".

\- gene: gene symbol.

\- stated\_length: the length written in the header, as a number; empty if absent or NA.

\- note: any note field in the header; otherwise empty.

\- actual\_length: number of bases in the sequence (across all its lines).



\## Other AI use

Used Claude (Cowork) to draft regex scripts.

I reviewed the scripts, ran and checked them against the raw data, and wrote

the comparison and analysis myself. I also used Claude to draft the prompt for Task 2 AI-assisted extraction, as well as troubleshoot commands.



