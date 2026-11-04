"""
CostConformal-Return - Stage 1
Convert the six official ASOS GraphReturns pickle (.p) files into
gzip-compressed CSV working copies for R.

WHY THIS STEP EXISTS
---------------------
The official release ships Python pickle files. R does not reliably or
safely read arbitrary Python pickles without a Python bridge, so this
one-time, Python-only step produces CSV working copies. The original .p
files remain the official source; the .csv.gz files are converted copies
only - no rows, labels, or values are changed by this conversion.

WHAT THIS SCRIPT DOES
----------------------
1. Reads each of the 6 official .p files with pandas.
2. Renames duplicate column headers (e.g. two columns both literally named
   "customerId_level_return_code_D") by appending "__duplicate2",
   "__duplicate3", etc. to the *second and later* occurrences only.
   Nothing is deleted here - the strict modelling stage is what excludes
   the ambiguous return-reason columns later, so no information is lost
   silently at conversion time.
3. Writes every hash(...) identifier column as TEXT (pandas "string"
   dtype), never as a numeric type. Hashed IDs are 64-bit signed integers;
   round-tripping them through a floating-point/CSV numeric path can lose
   precision and silently corrupt every downstream join.
4. Writes each table to <output_dir>/<original_stem>.csv.gz.
5. Writes a conversion_manifest.json recording, per file: source filename,
   output filename, row/column counts, the full column rename mapping, and
   which columns were forced to text.
6. Writes CHECKSUMS.sha256 over the six .csv.gz outputs, so you (or anyone
   re-running this) can verify the converted files were not altered later.
7. Cross-checks the row/column counts against the officially documented
   shapes and prints a clear PASS/MISMATCH per file (a mismatch is not
   fatal - it's a loud warning, since you may be using a different release
   version - but it should not be ignored without understanding why).

USAGE
-----
    pip install pandas
    python stage1_convert_pickle_to_csv.py

Run this from the project root (the folder containing data/raw_pickle/).
Defaults assume the folder structure described in the project README:

    data/raw_pickle/   -> put the 6 original .p files here
    data/raw_csv_gz/   -> this script writes its output here

Both paths can be overridden with --input-dir / --output-dir if your raw
files live somewhere else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

# ----------------------------------------------------------------------
# Officially documented shapes (rows, columns), used only as a sanity
# check after conversion - see the project's Dataset Identification
# section. A mismatch is reported but does not stop the script, since it
# may simply mean you downloaded a different snapshot of the release.
# ----------------------------------------------------------------------
EXPECTED_SHAPES = {
    "event_table_training.p": (1_369_133, 3),
    "event_table_testing.p": (1_460_366, 3),
    "customer_nodes_training.p": (777_001, 30),
    "customer_nodes_testing.p": (825_598, 30),
    "product_nodes_training.p": (411_495, 44),
    "product_nodes_testing.p": (411_544, 44),
}

REQUIRED_FILES = list(EXPECTED_SHAPES.keys())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw_pickle"),
        help="Folder containing the six official .p files (default: data/raw_pickle)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw_csv_gz"),
        help="Folder to write the six .csv.gz working copies into (default: data/raw_csv_gz)",
    )
    return parser.parse_args()


def make_unique_columns(columns) -> tuple[list[str], list[dict]]:
    """
    Rename duplicate headers by suffixing the 2nd, 3rd, ... occurrence with
    "__duplicateN". The FIRST occurrence of a name is left untouched, so
    existing R code that references the original column name still finds it.
    Nothing is dropped - every original column survives under some name.
    """
    counts: dict[str, int] = {}
    unique: list[str] = []
    mapping: list[dict] = []
    for col in map(str, columns):
        counts[col] = counts.get(col, 0) + 1
        occurrence = counts[col]
        new_name = col if occurrence == 1 else f"{col}__duplicate{occurrence}"
        unique.append(new_name)
        mapping.append({"original": col, "converted": new_name, "occurrence": occurrence})
    return unique, mapping


def convert_file(path: Path, output_dir: Path) -> dict:
    print(f"Reading  {path.name} ...", flush=True)
    df = pd.read_pickle(path)
    original_shape = list(df.shape)

    unique_cols, mapping = make_unique_columns(df.columns)
    df.columns = unique_cols

    # Preserve every hashed identifier as text so R never touches it as a number.
    id_columns = [c for c in df.columns if c.startswith("hash(")]
    for col in id_columns:
        df[col] = df[col].astype("string")

    out_path = output_dir / f"{path.stem}.csv.gz"
    print(f"Writing  {out_path.name} ...", flush=True)
    df.to_csv(
        out_path,
        index=False,
        compression={"method": "gzip", "compresslevel": 6, "mtime": 0},
        na_rep="",
        float_format="%.17g",
    )

    meta = {
        "source_file": path.name,
        "output_file": out_path.name,
        "rows": int(original_shape[0]),
        "columns": int(original_shape[1]),
        "column_name_mapping": mapping,
        "duplicate_columns_renamed": [m for m in mapping if m["occurrence"] > 1],
        "hash_id_columns_written_as_text": id_columns,
        "converted_dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "output_bytes": out_path.stat().st_size,
    }

    expected = EXPECTED_SHAPES.get(path.name)
    if expected is not None:
        status = "PASS" if tuple(original_shape) == expected else "MISMATCH"
        print(
            f"  Shape check: {status} - got {tuple(original_shape)}, "
            f"expected {expected}",
            flush=True,
        )
        meta["shape_check"] = {
            "expected": list(expected),
            "actual": original_shape,
            "status": status,
        }

    if meta["duplicate_columns_renamed"]:
        renamed = [m["converted"] for m in meta["duplicate_columns_renamed"]]
        print(f"  Duplicate headers renamed: {renamed}", flush=True)

    del df
    return meta


def write_checksums(output_dir: Path, csv_files: list[Path]) -> Path:
    checksum_path = output_dir / "CHECKSUMS.sha256"
    lines = []
    for f in sorted(csv_files):
        digest = hashlib.sha256()
        with open(f, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        lines.append(f"{digest.hexdigest()}  {f.name}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def main() -> None:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in REQUIRED_FILES if not (input_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required .p file(s) in "
            f"{input_dir.resolve()}:\n  - " + "\n  - ".join(missing)
        )

    manifest = {
        "dataset": "ASOS GraphReturns",
        "format": "gzip-compressed CSV",
        "notes": [
            "Original official files are .p (Python pickle); these .csv.gz "
            "files are converted working copies only - rows and values are "
            "unchanged.",
            "All hash(...) identifier columns are written as text to avoid "
            "64-bit precision loss when read into R.",
            "Duplicate source headers are preserved (not deleted) with "
            "__duplicateN suffixes on the 2nd+ occurrence.",
            "Training and testing files are never combined.",
        ],
        "files": [],
    }

    for name in REQUIRED_FILES:
        meta = convert_file(input_dir / name, output_dir)
        manifest["files"].append(meta)

    manifest_path = output_dir / "conversion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written:  {manifest_path}")

    csv_outputs = [output_dir / f"{Path(name).stem}.csv.gz" for name in REQUIRED_FILES]
    checksum_path = write_checksums(output_dir, csv_outputs)
    print(f"Checksums written: {checksum_path}")

    mismatches = [
        f["source_file"]
        for f in manifest["files"]
        if f.get("shape_check", {}).get("status") == "MISMATCH"
    ]
    if mismatches:
        print(
            "\nWARNING: shape mismatch vs. the officially documented row/"
            f"column counts for: {mismatches}. Conversion still completed - "
            "double-check you downloaded the intended release version."
        )
    else:
        print("\nAll six files match the officially documented shapes. Stage 1 complete.")


if __name__ == "__main__":
    main()