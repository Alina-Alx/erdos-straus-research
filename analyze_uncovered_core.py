#!/usr/bin/env python3
"""Analyze the uncovered core from the n == 1 mod 24 greedy cover."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from attack_1_mod_24 import (
    DEFAULT_GLOBAL_MODULUS,
    Rule,
    cover_modulus,
    find_minimal_general_key,
    lcm_many,
    rule_covers_residue,
)
from erdos_straus import check_solution


PRIMES = (5, 7, 11, 13, 17)


def is_quadratic_residue(value: int, modulus: int) -> bool:
    residue = value % modulus
    return any((x * x) % modulus == residue for x in range(modulus))


def square_roots_mod(value: int, modulus: int, limit: int = 20) -> list[int]:
    residue = value % modulus
    roots = [x for x in range(modulus) if (x * x) % modulus == residue]
    return roots[:limit]


def is_integer_square(value: int) -> tuple[bool, int | None]:
    root = math.isqrt(value)
    if root * root == value:
        return True, root
    return False, None


def uncovered_path(global_modulus: int) -> Path:
    return Path(f"uncovered_1_mod_24_global_{global_modulus}.csv")


def ensure_uncovered_file(global_modulus: int, max_d: int) -> Path:
    path = uncovered_path(global_modulus)
    if path.exists():
        return path

    _, uncovered, _ = cover_modulus(global_modulus, max_d)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["residue", "modulus"])
        writer.writeheader()
        for residue in uncovered:
            writer.writerow({"residue": residue, "modulus": global_modulus})
    return path


def load_uncovered(path: Path) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append((int(row["residue"]), int(row["modulus"])))
    return rows


def rule_modulus_from_pair(a: int, b: int) -> int:
    return lcm_many(4, a, b)


def reason_not_global_safe(residue: int, global_modulus: int, rule: Rule) -> str:
    if global_modulus % rule.rule_modulus != 0:
        return "rule_modulus does not divide GLOBAL"
    if not rule_covers_residue(rule, residue, global_modulus):
        return "condition fails for residue"
    return "other"


def targeted_lift_stats(residue: int, global_modulus: int, rule: Rule) -> tuple[int, int, int, int]:
    refined_modulus = lcm_many(global_modulus, rule_modulus_from_pair(rule.a, rule.b))
    total = refined_modulus // global_modulus
    covered = 0
    for k in range(total):
        subresidue = residue + k * global_modulus
        if rule_covers_residue(rule, subresidue, refined_modulus):
            covered += 1
    return refined_modulus, total, covered, total - covered


def write_feature_csv(rows: list[dict[str, object]]) -> Path:
    path = Path("uncovered_core_features.csv")
    fieldnames = [
        "residue",
        "modulus",
        "r_mod_24",
        "r_mod_5",
        "r_mod_7",
        "r_mod_11",
        "r_mod_13",
        "r_mod_17",
        "gcd_r_modulus",
        "is_square_integer",
        "integer_square_root",
        "is_quadratic_residue_mod_5",
        "is_quadratic_residue_mod_7",
        "is_quadratic_residue_mod_11",
        "is_quadratic_residue_mod_13",
        "is_quadratic_residue_mod_17",
        "is_quadratic_residue_mod_global",
        "square_roots_mod_global",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_sample_csv(rows: list[dict[str, object]]) -> Path:
    path = Path("uncovered_core_samples.csv")
    fieldnames = [
        "r",
        "n",
        "d",
        "a",
        "b",
        "x",
        "y",
        "z",
        "verified",
        "rule_modulus",
        "lcm_120120_rule_modulus",
        "reason_not_covered",
        "targeted_M",
        "total_subresidues",
        "covered_subresidues",
        "uncovered_subresidues",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze uncovered core modulo GLOBAL.")
    parser.add_argument("--global-modulus", type=int, default=DEFAULT_GLOBAL_MODULUS)
    parser.add_argument("--max-d", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = ensure_uncovered_file(args.global_modulus, args.max_d)
    uncovered = load_uncovered(path)

    feature_rows: list[dict[str, object]] = []
    sample_rows: list[dict[str, object]] = []
    d_counts: Counter[int] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    reason_counts: Counter[str] = Counter()
    rule_modulus_counts: Counter[int] = Counter()
    lift_full_count = 0
    all_prime_qr_count = 0
    global_qr_count = 0
    integer_square_examples: list[tuple[int, int]] = []
    global_square_examples: list[tuple[int, list[int]]] = []

    for residue, modulus in uncovered:
        is_square, square_root = is_integer_square(residue)
        qr_flags = {prime: is_quadratic_residue(residue, prime) for prime in PRIMES}
        is_global_qr = is_quadratic_residue(residue, modulus)
        roots = square_roots_mod(residue, modulus)

        if all(qr_flags.values()):
            all_prime_qr_count += 1
        if is_global_qr:
            global_qr_count += 1
            global_square_examples.append((residue, roots))
        if is_square:
            integer_square_examples.append((residue, int(square_root)))

        feature_rows.append(
            {
                "residue": residue,
                "modulus": modulus,
                "r_mod_24": residue % 24,
                "r_mod_5": residue % 5,
                "r_mod_7": residue % 7,
                "r_mod_11": residue % 11,
                "r_mod_13": residue % 13,
                "r_mod_17": residue % 17,
                "gcd_r_modulus": math.gcd(residue, modulus),
                "is_square_integer": is_square,
                "integer_square_root": "" if square_root is None else square_root,
                "is_quadratic_residue_mod_5": qr_flags[5],
                "is_quadratic_residue_mod_7": qr_flags[7],
                "is_quadratic_residue_mod_11": qr_flags[11],
                "is_quadratic_residue_mod_13": qr_flags[13],
                "is_quadratic_residue_mod_17": qr_flags[17],
                "is_quadratic_residue_mod_global": is_global_qr,
                "square_roots_mod_global": " ".join(str(root) for root in roots),
            }
        )

        n = residue if residue > 1 else residue + modulus
        solution = find_minimal_general_key(n, args.max_d)
        if solution is None:
            sample_rows.append(
                {
                    "r": residue,
                    "n": n,
                    "d": "",
                    "a": "",
                    "b": "",
                    "x": "",
                    "y": "",
                    "z": "",
                    "verified": False,
                    "rule_modulus": "",
                    "lcm_120120_rule_modulus": "",
                    "reason_not_covered": "sample has no general_key up to max_d",
                    "targeted_M": "",
                    "total_subresidues": "",
                    "covered_subresidues": "",
                    "uncovered_subresidues": "",
                }
            )
            continue

        x, y, z, d, a, b = solution
        rule = Rule(d=d, a=a, b=b)
        verified = check_solution(n, x, y, z)
        basic_rule_modulus = rule_modulus_from_pair(a, b)
        lifted_modulus = lcm_many(modulus, basic_rule_modulus)
        reason = reason_not_global_safe(residue, modulus, rule)
        if reason == "rule_modulus does not divide GLOBAL":
            refined, total, covered, still_uncovered = targeted_lift_stats(residue, modulus, rule)
            if covered and still_uncovered:
                reason = "rule covers only subresidues after lifting"
            elif covered == total:
                reason = "rule covers all lifted subresidues"
        else:
            refined, total, covered, still_uncovered = targeted_lift_stats(residue, modulus, rule)

        if covered == total:
            lift_full_count += 1
        d_counts[d] += 1
        pair_counts[(a, b)] += 1
        reason_counts[reason] += 1
        rule_modulus_counts[basic_rule_modulus] += 1

        sample_rows.append(
            {
                "r": residue,
                "n": n,
                "d": d,
                "a": a,
                "b": b,
                "x": x,
                "y": y,
                "z": z,
                "verified": verified,
                "rule_modulus": basic_rule_modulus,
                "lcm_120120_rule_modulus": lifted_modulus,
                "reason_not_covered": reason,
                "targeted_M": refined,
                "total_subresidues": total,
                "covered_subresidues": covered,
                "uncovered_subresidues": still_uncovered,
            }
        )

    features_path = write_feature_csv(feature_rows)
    samples_path = write_sample_csv(sample_rows)

    total = len(uncovered)
    print(f"GLOBAL modulus: {args.global_modulus}")
    print(f"uncovered CSV: {path}")
    print(f"feature CSV: {features_path}")
    print(f"sample CSV: {samples_path}")
    print()

    print("summary:")
    print(f"  uncovered residues total: {total}")
    print(f"  all are r == 1 mod 24: {all(row['r_mod_24'] == 1 for row in feature_rows)}")
    print(f"  gcd(r, GLOBAL)=1 count: {sum(1 for row in feature_rows if row['gcd_r_modulus'] == 1)}")
    print(f"  integer squares count: {len(integer_square_examples)}")
    print(f"  quadratic residues modulo all primes {PRIMES}: {all_prime_qr_count}")
    print(f"  quadratic residues modulo GLOBAL: {global_qr_count}")
    print(f"  non-quadratic-like by prime flags: {total - all_prime_qr_count}")
    print(f"  targeted lifts covering full refined class: {lift_full_count}")
    print()

    print("first 30 uncovered residues:")
    print([residue for residue, _ in uncovered[:30]])
    print()

    print("first 30 integer-square residues:")
    print(integer_square_examples[:30])
    print()

    print("first 30 residues represented as squares modulo GLOBAL:")
    for residue, roots in global_square_examples[:30]:
        print(f"  r={residue}: roots={roots[:8]}")
    print()

    print("top d for sample n:")
    for d, count in d_counts.most_common(20):
        print(f"  d={d}: {count}")
    print()

    print("top pairs for sample n:")
    for pair, count in pair_counts.most_common(20):
        print(f"  {pair}: {count}")
    print()

    print("top rule_modulus values:")
    for rule_modulus, count in rule_modulus_counts.most_common(20):
        print(f"  {rule_modulus}: {count}")
    print()

    print("why greedy cover missed these residues:")
    for reason, count in reason_counts.most_common():
        print(f"  {reason}: {count}")
    print()

    print("targeted lift examples:")
    for row in sample_rows[:30]:
        print(
            f"  r={row['r']}, d={row['d']}, pair=({row['a']},{row['b']}), "
            f"M={row['targeted_M']}, covered={row['covered_subresidues']}/"
            f"{row['total_subresidues']}, reason={row['reason_not_covered']}"
        )
    print()

    print("next-step assessment:")
    print("  - increasing GLOBAL helps only if it includes the rule_modulus factors needed by the core")
    print("  - targeted lift is useful diagnostically, but many sample rules cover only subresidues")
    print("  - the square-like core is strongly supported by the residue data")
    print("  - a separate lemma for the square-like part of n == 1 mod 24 looks like the best next target")
    print("verdict: not proved yet")


if __name__ == "__main__":
    main()
