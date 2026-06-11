#!/usr/bin/env python3
"""Diagnose residue classes not covered by conservative proof search."""

from __future__ import annotations

import argparse
import math
from collections import Counter

from erdos_straus import check_solution, first_compatible_d, formula_general_key
from prove_by_residues import assign_residues


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def factorize(value: int) -> dict[int, int]:
    n = value
    factors: dict[int, int] = {}
    p = 2
    while p * p <= n:
        while n % p == 0:
            factors[p] = factors.get(p, 0) + 1
            n //= p
        p += 1 if p == 2 else 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def missing_prime_factors(rule_modulus: int, base_modulus: int) -> dict[int, int]:
    rule_factors = factorize(rule_modulus)
    base_factors = factorize(base_modulus)
    missing: dict[int, int] = {}
    for prime, exponent in rule_factors.items():
        if base_factors.get(prime, 0) < exponent:
            missing[prime] = exponent - base_factors.get(prime, 0)
    return missing


def square_roots_mod(residue: int, modulus: int, max_roots: int = 12) -> list[int]:
    roots = [x for x in range(modulus) if (x * x) % modulus == residue % modulus]
    return roots[:max_roots]


def find_minimal_general_key(n: int, max_d: int) -> tuple[int, int, int, int, int, int] | None:
    for d in range(first_compatible_d(n), max_d + 1, 4):
        solution = formula_general_key(n, d)
        if solution is not None:
            return solution
    return None


def print_residue_properties(modulus: int, residues: list[int]) -> None:
    print("residue properties:")
    print(
        "L | residue | mod8 | mod12 | mod24 | mod60 | mod120 | mod840 | gcd(r,L) | square_roots_mod_L"
    )
    print(
        "- | ------- | ---- | ----- | ----- | ----- | ------ | ------ | -------- | ------------------"
    )
    for residue in residues:
        roots = square_roots_mod(residue, modulus)
        root_text = ", ".join(str(root) for root in roots) if roots else "none"
        if len(roots) == 12:
            root_text += ", ..."
        print(
            f"{modulus} | {residue} | {residue % 8} | {residue % 12} | "
            f"{residue % 24} | {residue % 60} | {residue % 120} | "
            f"{residue % 840} | {math.gcd(residue, modulus)} | {root_text}"
        )
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose uncovered residue classes.")
    parser.add_argument("--modulus", type=int, required=True)
    parser.add_argument("--max-d", type=int, default=5000)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument(
        "--residues",
        default="",
        help="optional comma-separated residue list; otherwise use proof-search uncovered residues",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.modulus < 1:
        raise SystemExit("--modulus must be positive")
    if args.max_d < 1:
        raise SystemExit("--max-d must be positive")
    if args.samples < 1:
        raise SystemExit("--samples must be positive")

    if args.residues:
        residues = sorted({int(part.strip()) for part in args.residues.split(",") if part.strip()})
    else:
        _, _, uncovered = assign_residues(
            modulus=args.modulus,
            max_d=args.max_d,
            search_cover=True,
        )
        residues = sorted(uncovered)

    print(f"modulus: {args.modulus}")
    print(f"max_d: {args.max_d}")
    print(f"uncovered residues diagnosed: {residues}")
    print()

    print_residue_properties(args.modulus, residues)

    d_counts: Counter[int] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    rule_modulus_counts: Counter[int] = Counter()
    missing_factor_counts: Counter[str] = Counter()

    print("sample diagnostics:")
    print("L | residue | sample n | d | a | b | x | y | z | verified | rule_modulus | missing_from_L")
    print("- | ------- | -------- | - | - | - | - | - | - | -------- | ------------ | --------------")
    for residue in residues:
        sample_count = 0
        k = 0
        while sample_count < args.samples:
            n = residue + k * args.modulus
            k += 1
            if n <= 1:
                continue

            solution = find_minimal_general_key(n, args.max_d)
            if solution is None:
                print(
                    f"{args.modulus} | {residue} | {n} | not_found |  |  |  |  |  | False |  | "
                )
                sample_count += 1
                continue

            x, y, z, d, a, b = solution
            verified = check_solution(n, x, y, z)
            rule_modulus = lcm_many(4, a, b)
            missing = missing_prime_factors(rule_modulus, args.modulus)
            missing_text = "none" if not missing else " ".join(
                f"{prime}^{exp}" for prime, exp in sorted(missing.items())
            )

            d_counts[d] += 1
            pair_counts[(a, b)] += 1
            rule_modulus_counts[rule_modulus] += 1
            missing_factor_counts[missing_text] += 1

            print(
                f"{args.modulus} | {residue} | {n} | {d} | {a} | {b} | "
                f"{x} | {y} | {z} | {verified} | {rule_modulus} | {missing_text}"
            )
            sample_count += 1

    print()
    print("d counts:")
    for d, count in d_counts.most_common():
        print(f"  d={d}: {count}")
    print()

    print("pair counts:")
    for pair, count in pair_counts.most_common():
        print(f"  {pair}: {count}")
    print()

    print("rule_modulus counts:")
    for rule_modulus, count in rule_modulus_counts.most_common():
        print(f"  {rule_modulus}: {count}")
    print()

    print("prime factors missing from old L:")
    for missing, count in missing_factor_counts.most_common():
        print(f"  {missing}: {count}")


if __name__ == "__main__":
    main()
