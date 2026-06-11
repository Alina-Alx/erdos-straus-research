#!/usr/bin/env python3
"""Small tools for exploring the Erdos-Straus conjecture.

The conjecture says that for every integer n >= 2 there are positive
integers x, y, z such that:

    4/n = 1/x + 1/y + 1/z
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from fractions import Fraction
from typing import Optional


Solution = tuple[int, int, int]
GeneralSolution = tuple[int, int, int, int, int, int]


def formula_even(n: int) -> Optional[Solution]:
    """Formula for every even n.

    4/n = 1/(n/2) + 1/n + 1/n
    """
    if n % 2 != 0:
        return None
    return (n // 2, n, n)


def formula_divisible_by_3(n: int) -> Optional[Solution]:
    """Formula for every n divisible by 3.

    If n = 3k, then:
    4/n = 1/k + 1/(2n) + 1/(2n)
    """
    if n % 3 != 0:
        return None
    return (n // 3, 2 * n, 2 * n)


def formula_3_mod_4(n: int) -> Optional[Solution]:
    """Formula for every n == 3 mod 4.

    4/n = 1/((n+1)/4) + 1/(n(n+1)/2) + 1/(n(n+1)/2)
    """
    if n % 4 != 3:
        return None
    return ((n + 1) // 4, n * (n + 1) // 2, n * (n + 1) // 2)


def check_solution(n: int, x: int, y: int, z: int) -> bool:
    """Check a proposed solution exactly, without floating-point rounding."""
    if n < 2 or min(x, y, z) <= 0:
        return False

    left = Fraction(4, n)
    right = Fraction(1, x) + Fraction(1, y) + Fraction(1, z)
    return left == right


def formula_general_key(n: int, d: int) -> Optional[GeneralSolution]:
    """Try the general key x = (n + d) / 4.

    If a + b = 4d and both a and b divide N = n(n+d), then:

        x = (n+d)/4
        y = N/a
        z = N/b

    gives 4/n = 1/x + 1/y + 1/z.
    """
    if d <= 0:
        return None
    if (n + d) % 4 != 0:
        return None

    x = (n + d) // 4
    if x <= 0:
        return None

    product = n * (n + d)
    pair_sum = 4 * d

    # Pairs are symmetric in y and z, so a <= b is enough.
    for a in range(1, pair_sum // 2 + 1):
        b = pair_sum - a
        if product % a != 0 or product % b != 0:
            continue

        y = product // a
        z = product // b
        if check_solution(n, x, y, z):
            return (x, y, z, d, a, b)

    return None


def first_compatible_d(n: int) -> int:
    """Smallest positive d such that n + d is divisible by 4."""
    d = (-n) % 4
    return d if d > 0 else 4


def brute_force_solution(n: int, limit: int = 100_000) -> Optional[Solution]:
    """Search for x <= y <= z by looping over x and y, then computing z.

    For fixed n, x, y:

        remaining = 4/n - 1/x - 1/y

    If remaining is exactly 1/z for an integer z, we found a solution.
    """
    target = Fraction(4, n)

    # Since x <= y <= z, we know 4/n <= 3/x, so x <= 3n/4.
    # Also x must be bigger than n/4, otherwise 1/x is already too large.
    x_min = n // 4 + 1
    x_max = min(limit, (3 * n) // 4 + 1)

    for x in range(x_min, x_max + 1):
        after_x = target - Fraction(1, x)
        if after_x <= 0:
            continue

        # With y <= z, remaining after x is at most 2/y.
        y_max = min(limit, (2 * after_x.denominator) // after_x.numerator)

        for y in range(x, y_max + 1):
            remaining = after_x - Fraction(1, y)
            if remaining <= 0:
                continue

            # Fraction normalizes automatically. 1/z has numerator 1.
            if remaining.numerator != 1:
                continue

            z = remaining.denominator
            if y <= z <= limit and check_solution(n, x, y, z):
                return (x, y, z)

    return None


def empty_row(n: int, method: str) -> dict[str, object]:
    return {
        "n": n,
        "method": method,
        "x": None,
        "y": None,
        "z": None,
        "d": None,
        "a": None,
        "b": None,
    }


def row_from_solution(n: int, method: str, solution: Solution) -> dict[str, object]:
    x, y, z = solution
    return {
        "n": n,
        "method": method,
        "x": x,
        "y": y,
        "z": z,
        "d": None,
        "a": None,
        "b": None,
    }


def solve_n(n: int, max_d: int = 500) -> dict[str, object]:
    """Solve one value using proved base formulas, then general keys.

    This function does not use brute force. If no formula is found up to
    max_d, it returns method="not_found" so the gap remains visible.
    """
    if n < 2:
        raise ValueError("n must be at least 2")
    if max_d < 1:
        raise ValueError("max_d must be positive")

    formulas = [
        ("formula_even", formula_even),
        ("formula_divisible_by_3", formula_divisible_by_3),
        ("formula_3_mod_4", formula_3_mod_4),
    ]

    for method, formula in formulas:
        solution = formula(n)
        if solution is None:
            continue

        x, y, z = solution
        if check_solution(n, x, y, z):
            return row_from_solution(n, method, solution)

    for d in range(first_compatible_d(n), max_d + 1, 4):
        solution = formula_general_key(n, d)
        if solution is None:
            continue

        x, y, z, used_d, a, b = solution
        return {
            "n": n,
            "method": f"general_key_d_{used_d}",
            "x": x,
            "y": y,
            "z": z,
            "d": used_d,
            "a": a,
            "b": b,
        }

    return empty_row(n, "not_found")


def add_analysis_columns(row: dict[str, object]) -> dict[str, object]:
    """Add modular-pattern columns used in the CSV and hard-case report."""
    n = int(row["n"])
    row = dict(row)
    row["verified"] = (
        row["x"] is not None
        and row["y"] is not None
        and row["z"] is not None
        and check_solution(n, int(row["x"]), int(row["y"]), int(row["z"]))
    )

    for modulus in (4, 8, 12, 24, 60, 120, 840):
        row[f"n_mod_{modulus}"] = n % modulus

    return row


def write_csv(rows: list[dict[str, object]], csv_path: str) -> None:
    """Write all results to a CSV file."""
    fieldnames = [
        "n",
        "method",
        "x",
        "y",
        "z",
        "verified",
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
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: list[dict[str, object]]) -> None:
    """Print the main result table."""
    print("n | method | x | y | z | verified | d | a | b")
    print("-- | ------ | - | - | - | -------- | - | - | -")
    for row in rows:
        print(
            f"{row['n']} | {row['method']} | {row['x']} | "
            f"{row['y']} | {row['z']} | {row['verified']} | "
            f"{row['d']} | {row['a']} | {row['b']}"
        )


def print_summary(rows: list[dict[str, object]], max_n: int, max_d: int, csv_path: str) -> None:
    """Print a compact research summary for a range run."""
    base_methods = {"formula_even", "formula_divisible_by_3", "formula_3_mod_4"}
    base_rows = [row for row in rows if row["method"] in base_methods]
    general_rows = [row for row in rows if str(row["method"]).startswith("general_key_d_")]
    missing = [int(row["n"]) for row in rows if row["method"] == "not_found"]
    unverified = [int(row["n"]) for row in rows if not row["verified"]]

    d_values = [int(row["d"]) for row in general_rows if row["d"] is not None]
    max_used_d = max(d_values) if d_values else None
    hardest = sorted(general_rows, key=lambda row: (int(row["d"]), int(row["n"])), reverse=True)[:10]

    if missing or unverified:
        print(f"range searched up to N: {max_n}")
    else:
        print(f"verified up to N: {max_n}")
    print(f"max_d searched: {max_d}")
    print(f"CSV written to: {csv_path}")
    print()

    print("coverage summary:")
    print(f"  base formulas: {len(base_rows)}")
    for method, count in Counter(str(row["method"]) for row in base_rows).most_common():
        print(f"    {method}: {count}")
    print(f"  general keys: {len(general_rows)}")
    print(f"  max d actually used: {max_used_d}")
    print(f"  not covered by formulas up to max_d: {len(missing)}")
    print(f"  unverified rows: {unverified}")
    print()

    print("not covered n:")
    print(missing if missing else [])
    print()

    print("top-10 hardest n by minimal d:")
    if not hardest:
        print("  none")
    for row in hardest:
        print(
            f"  n={row['n']}, d={row['d']}, pair=({row['a']}, {row['b']}), "
            f"x={row['x']}, y={row['y']}, z={row['z']}"
        )
    print()

    print("distribution of used d:")
    for d, count in Counter(d_values).most_common():
        print(f"  d={d}: {count}")
    print()

    print("distribution of pairs (a,b):")
    pair_values = [
        (int(row["a"]), int(row["b"]))
        for row in general_rows
        if row["a"] is not None and row["b"] is not None
    ]
    for pair, count in Counter(pair_values).most_common():
        print(f"  {pair}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explore the Erdos-Straus equation 4/n = 1/x + 1/y + 1/z."
    )
    parser.add_argument(
        "--max-n",
        type=int,
        default=300,
        help="solve every n from 2 through this value",
    )
    parser.add_argument(
        "--max-d",
        type=int,
        default=500,
        help="largest general-key d to try after the base formulas",
    )
    parser.add_argument(
        "--csv",
        default="results.csv",
        help="where to write the CSV export",
    )
    parser.add_argument(
        "--show-table",
        action="store_true",
        help="print every row instead of only the compact summary",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_n < 2:
        raise SystemExit("--max-n must be at least 2")
    if args.max_d < 1:
        raise SystemExit("--max-d must be positive")

    rows = [add_analysis_columns(solve_n(n, max_d=args.max_d)) for n in range(2, args.max_n + 1)]
    write_csv(rows, args.csv)

    if args.show_table:
        print_table(rows)
        print()
    print_summary(rows, args.max_n, args.max_d, args.csv)


if __name__ == "__main__":
    main()
