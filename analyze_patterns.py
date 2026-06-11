#!/usr/bin/env python3
"""Analyze formula usage from results.csv."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


CSV_PATH = Path(__file__).with_name("results.csv")
INT_COLUMNS = {
    "n",
    "x",
    "y",
    "z",
    "d",
    "a",
    "b",
    "n_mod_4",
    "n_mod_8",
    "n_mod_12",
    "n_mod_24",
    "n_mod_60",
    "n_mod_120",
    "n_mod_840",
}


def load_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            converted: dict[str, object] = {}
            for key, value in row.items():
                if key in INT_COLUMNS and value not in ("", None):
                    converted[key] = int(value)
                else:
                    converted[key] = value
            rows.append(converted)
    return rows


def is_general(row: dict[str, object]) -> bool:
    return str(row["method"]).startswith("general_key_d_")


def print_summary(rows: list[dict[str, object]]) -> None:
    general_rows = [row for row in rows if is_general(row)]
    missing = [row for row in rows if row["method"] == "not_found"]
    unverified = [row for row in rows if row["verified"] != "True"]

    print(f"Loaded {len(rows)} rows from {CSV_PATH.name}.")
    print(f"General-key rows: {len(general_rows)}")
    print(f"Not found rows: {len(missing)}")
    print(f"Unverified rows: {len(unverified)}")
    print()

    print("method distribution:")
    for method, count in Counter(str(row["method"]) for row in rows).most_common():
        print(f"  {method}: {count}")
    print()

    print("d distribution:")
    d_counts = Counter(int(row["d"]) for row in general_rows if row["d"] != "")
    for d, count in d_counts.most_common():
        print(f"  d={d}: {count}")
    print()

    print("pair distribution:")
    pair_counts = Counter(
        (int(row["a"]), int(row["b"]))
        for row in general_rows
        if row["a"] != "" and row["b"] != ""
    )
    for pair, count in pair_counts.most_common():
        print(f"  {pair}: {count}")
    print()

    hardest = sorted(
        general_rows,
        key=lambda row: (int(row["d"]), int(row["n"])),
        reverse=True,
    )[:10]
    print("top-10 hardest n by minimal d:")
    if not hardest:
        print("  none")
    for row in hardest:
        print(
            f"  n={row['n']}, d={row['d']}, pair=({row['a']}, {row['b']}), "
            f"x={row['x']}, y={row['y']}, z={row['z']}"
        )
    print()

    print("missing n:")
    print([row["n"] for row in missing] if missing else [])


def print_residue_groups(rows: list[dict[str, object]]) -> None:
    missing = [row for row in rows if row["method"] == "not_found"]
    if not missing:
        return

    for modulus in (60, 120, 840):
        groups: dict[int, list[int]] = defaultdict(list)
        for row in missing:
            groups[int(row[f"n_mod_{modulus}"])].append(int(row["n"]))
        print()
        print(f"missing grouped by n mod {modulus}:")
        for residue in sorted(groups):
            values = ", ".join(str(n) for n in groups[residue])
            print(f"  {residue}: {values}")


def main() -> None:
    rows = load_rows(CSV_PATH)
    print_summary(rows)
    print_residue_groups(rows)


if __name__ == "__main__":
    main()
