"""
Lab 3 - Task 1 (regex cleaning) for messy_sequences.fasta

Usage (from the repo root, with the conda env active):
    python scripts/clean_fasta.py data/raw/messy_sequences.fasta output/regex_sequences_clean.csv

The 8 headers in this file use 8 different layouts:
  sample_001|organism=Homo_sapiens|gene=BRCA1|len=120      pipes + key=value
  Sample002 organism:Homo sapiens gene:TP53                 spaces + key:value
  sample-003 | Homo_sapiens | EGFR | length=150bp           pipes, mostly no keys
  SAMPLE_004;species=H.sapiens;target=BRCA1                 semicolons, different key names
  sample005 Homo sapiens; TP53; 130 bp                      semicolons, no keys
  seq6|Hsapiens|EGFR                                        different ID prefix, no keys
  Sample_007 organism=Homo_sapiens|gene=BRCA1|note:re-sequenced   mixed = and :
  sample-8 species:Homo_sapiens gene:TP53 len:NA            spaces + key:value, NA length

Why one general parser instead of one regex per layout: with 8 records and
8 layouts, a regex per layout would just memorize this file. Instead we
  1) pull out the ID (always the first token),
  2) pull out any key=value / key:value pairs,
  3) classify whatever is left by what it LOOKS like (an organism name,
     a gene symbol, a "130 bp" length).
That is closer to how you'd handle a new file with a 9th layout.
"""

import re
import sys

import pandas as pd

# Different key names used for the same field -> one field name.
KEY_ALIASES = {
    "organism": "organism", "species": "organism",
    "gene": "gene", "target": "gene",
    "len": "stated_length", "length": "stated_length",
    "note": "note",
}

# key=value or key:value. The value runs until the next | or ; OR until the
# next "word=" / "word:" - that lookahead is what keeps "Homo sapiens" whole
# in "organism:Homo sapiens gene:TP53".
KV_PAIR = re.compile(
    r"([A-Za-z_]+)\s*[=:]\s*([^|;\s][^|;]*?)(?=\s*[|;]|\s+[A-Za-z_]+\s*[=:]|\s*$)")

# Every spelling of the species in this file: Homo_sapiens, Homo sapiens,
# H.sapiens, Hsapiens.
HUMAN = re.compile(r"^(?:homo[\s_]*sapiens|h\.?[\s_]*sapiens)$", re.IGNORECASE)
GENE_SYMBOL = re.compile(r"^[A-Z][A-Z0-9]{2,9}$")      # BRCA1, TP53, EGFR
BP_LENGTH = re.compile(r"^(\d+)\s*bp$", re.IGNORECASE)  # "130 bp"


def parse_id(token):
    # sample_001, Sample002, sample-003, SAMPLE_004, seq6, sample-8
    # -> "sample_001" ... "sample_008". Only the number identifies the record.
    m = re.fullmatch(r"([A-Za-z]+)[-_]?(\d+)", token)
    if not m:
        return token, f"unrecognized id '{token}'"
    new = f"sample_{int(m[2]):03d}"
    note = f"id prefix '{m[1]}' (not 'sample')" if m[1].lower() != "sample" else ""
    return new, note


def normalize_organism(text):
    if HUMAN.match(text.strip()):
        return "Homo sapiens"
    # Anything else: underscores -> spaces, "Genus species" capitalization.
    return text.replace("_", " ").strip().capitalize()


def parse_header(header):
    notes = []
    # Step 1: the ID is everything before the first | ; or space
    m = re.match(r"([^|;\s]+)(.*)", header.strip())
    first, rest = m[1], m[2]
    out ={"sample_id": None, "organism": None, "gene": None,
           "stated_length": None, "note": None}
    out["sample_id"], n = parse_id(first)
    notes.append(n)

    # Which separators this header uses (reported, useful for the write-up)
    seps = [name for sym, name in [("|", "pipe"), (";", "semicolon"),
                                   ("=", "key=value"), (":", "key:value")] if sym in rest]
    style = "+".join(seps) if seps else "space"

    # Step 2: key/value pairs
    for k, v in KV_PAIR.findall(rest):
        field = KEY_ALIASES.get(k.lower())
        if field is None:
            notes.append(f"unknown key '{k}'")
            continue
        out[field] = v.strip()
        if k.lower() not in ("organism", "gene", "len", "note"):
            notes.append(f"key '{k}' read as {field}")
    leftover = KV_PAIR.sub("", rest)

    # Step 3: positional tokens (no key) - classify by appearance
    for tok in (t.strip() for t in re.split(r"[|;]", leftover)):
        if not tok:
            continue
        if out["organism"] is None and HUMAN.match(tok):
            out["organism"] = tok
        elif out["gene"] is None and GENE_SYMBOL.match(tok):
            out["gene"] = tok
        elif out["stated_length"] is None and BP_LENGTH.match(tok):
            out["stated_length"] = tok
        elif out["organism"] is None and re.fullmatch(r"[A-Z][a-z]+[\s_][a-z]+", tok):
            out["organism"] = tok  # some other "Genus species"
        else:
            notes.append(f"unclassified token '{tok}'")

    if out["organism"]:
        original = out["organism"]
        out["organism"] = normalize_organism(original)
        if original not in ("Homo sapiens",):
            notes.append(f"organism '{original}' -> {out['organism']}")

    # Stated length: "120", "150bp", "130 bp" -> number; "NA" -> missing
    sl = out["stated_length"]
    if sl is not None:
        m = re.search(r"\d+", sl)
        if m:
            out["stated_length"] = int(m.group())
        else:
            notes.append(f"stated length '{sl}' -> missing")
            out["stated_length"] = None

    return out, style, notes


def read_fasta(path):
    """Yield (header, sequence). Sequences here wrap over several lines."""
    header, chunks = None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks)
                header, chunks = line[1:], []
            else:
                chunks.append(line)
    if header is not None:
        yield header, "".join(chunks)


def main(in_path, out_path):
    rows = []
    for header, seq in read_fasta(in_path):
        fields, style, notes = parse_header(header)
        seq = re.sub(r"[^A-Za-z]", "", seq).upper()
        if re.search(r"[^ACGTN]", seq):
            notes.append("non-ACGTN characters in sequence")
        fields.update({
            "actual_length": len(seq),
            "gc_content": round((seq.count("G") + seq.count("C")) / len(seq), 3) if seq else None,
            "header_style": style,
        })
        # The header's stated length vs what's really there - a mismatch
        # means either the header or the sequence is wrong.
        if fields["stated_length"] is not None and fields["stated_length"] != len(seq):
            notes.append(f"LENGTH MISMATCH: header says {fields['stated_length']}, sequence is {len(seq)}")
        fields["parse_notes"] = "; ".join(n for n in notes if n)
        fields["raw_header"] = header
        fields["sequence"] = seq
        rows.append(fields)

    df = pd.DataFrame(rows)
    # Int64 (capital I) = whole numbers that can still be missing; without
    # it pandas turns the column into 120.0, 150.0 because of the NA.
    df["stated_length"] = df["stated_length"].astype("Int64")
    df.to_csv(out_path, index=False)
    print(f"Parsed {len(df)} sequences -> {out_path}\n")
    print(df[["sample_id", "organism", "gene", "stated_length", "actual_length",
              "header_style"]].to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/clean_fasta.py <raw_fasta> <output_csv>")
    main(sys.argv[1], sys.argv[2])
