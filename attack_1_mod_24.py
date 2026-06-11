#!/usr/bin/env python3
"""Focused attack on the subproblem n == 1 mod 24.

This is a research tool, not a proof by itself.  It separates:
- sample verification up to a finite max_n;
- residue-safe coverage for chosen moduli;
- greedy finite cover modulo an explicit GLOBAL modulus.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from erdos_straus import check_solution, first_compatible_d, formula_general_key, solve_n


PRIMES_TO_TEST = (5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43)
MULTI_PRIME_PREFIXES = (
    (5, 7),
    (5, 7, 11),
    (5, 7, 11, 13),
    (5, 7, 11, 13, 17),
    (5, 7, 11, 13, 17, 19),
)
DEFAULT_GLOBAL_MODULUS = 24 * 5 * 7 * 11 * 13


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def method(self) -> str:
        return f"general_key_d_{self.d}"

    @property
    def rule_modulus(self) -> int:
        return lcm_many(24, 4, self.a, self.b)


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def divisors(value: int) -> list[int]:
    small: list[int] = []
    large: list[int] = []
    for candidate in range(1, math.isqrt(value) + 1):
        if value % candidate == 0:
            small.append(candidate)
            if candidate * candidate != value:
                large.append(value // candidate)
    return small + large[::-1]


def find_minimal_general_key(n: int, max_d: int) -> tuple[int, int, int, int, int, int] | None:
    for d in range(first_compatible_d(n), max_d + 1, 4):
        solution = formula_general_key(n, d)
        if solution is not None:
            return solution
    return None


def covered_by_smaller_divisor(n: int, max_d: int, cache: dict[int, bool]) -> int | None:
    """Return a covered proper divisor m > 1, if one is found."""
    for candidate in range(2, math.isqrt(n) + 1):
        if n % candidate != 0:
            continue
        for divisor in (candidate, n // candidate):
            if divisor <= 1 or divisor >= n:
                continue
            if divisor not in cache:
                cache[divisor] = solve_n(divisor, max_d=max_d)["method"] != "not_found"
            if cache[divisor]:
                return divisor
    return None


def sample_scan(args: argparse.Namespace) -> None:
    rows: list[dict[str, object]] = []
    missing: list[int] = []
    unverified: list[int] = []
    d_over_limit: list[int] = []
    d_counts: Counter[int] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    divisor_cache: dict[int, bool] = {}
    reduced_count = 0

    for n in range(25, args.max_n + 1, 24):
        if args.reduce_by_divisors:
            divisor = covered_by_smaller_divisor(n, args.max_d, divisor_cache)
            if divisor is not None:
                reduced_count += 1
                rows.append(
                    {
                        "n": n,
                        "d": "",
                        "a": "",
                        "b": "",
                        "x": "",
                        "y": "",
                        "z": "",
                        "verified": True,
                        "covered_by_divisor": divisor,
                        "n_mod_120": n % 120,
                        "n_mod_840": n % 840,
                        "n_mod_2520": n % 2520,
                        "n_mod_27720": n % 27720,
                    }
                )
                continue

        solution = find_minimal_general_key(n, args.max_d)
        if solution is None:
            missing.append(n)
            rows.append(
                {
                    "n": n,
                    "d": "",
                    "a": "",
                    "b": "",
                    "x": "",
                    "y": "",
                    "z": "",
                    "verified": False,
                    "covered_by_divisor": "",
                    "n_mod_120": n % 120,
                    "n_mod_840": n % 840,
                    "n_mod_2520": n % 2520,
                    "n_mod_27720": n % 27720,
                }
            )
            continue

        x, y, z, d, a, b = solution
        verified = check_solution(n, x, y, z)
        if not verified:
            unverified.append(n)
        if d > args.max_d:
            d_over_limit.append(n)
        d_counts[d] += 1
        pair_counts[(a, b)] += 1
        rows.append(
            {
                "n": n,
                "d": d,
                "a": a,
                "b": b,
                "x": x,
                "y": y,
                "z": z,
                "verified": verified,
                "covered_by_divisor": "",
                "n_mod_120": n % 120,
                "n_mod_840": n % 840,
                "n_mod_2520": n % 2520,
                "n_mod_27720": n % 27720,
            }
        )

    output_path = Path(args.output)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "n",
                "d",
                "a",
                "b",
                "x",
                "y",
                "z",
                "verified",
                "covered_by_divisor",
                "n_mod_120",
                "n_mod_840",
                "n_mod_2520",
                "n_mod_27720",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    general_rows = [row for row in rows if row["d"] != ""]
    hardest = sorted(general_rows, key=lambda row: (int(row["d"]), int(row["n"])), reverse=True)[:20]

    print(f"sample scan for n == 1 mod 24 up to {args.max_n}")
    print(f"rows written: {output_path}")
    print(f"checked count: {len(rows)}")
    print(f"covered by smaller divisor: {reduced_count}")
    print(f"general-key solved count: {len(general_rows)}")
    print(f"missing count: {len(missing)}")
    print(f"unverified count: {len(unverified)}")
    print(f"max d: {max(d_counts) if d_counts else None}")
    print(f"n with d > {args.max_d}: {d_over_limit}")
    print(f"missing n: {missing[:200]}{' ...' if len(missing) > 200 else ''}")
    print(f"unverified n: {unverified[:200]}{' ...' if len(unverified) > 200 else ''}")
    print()

    print("top-20 d:")
    for d, count in d_counts.most_common(20):
        print(f"  d={d}: {count}")
    print()

    print("top-20 pairs:")
    for pair, count in pair_counts.most_common(20):
        print(f"  {pair}: {count}")
    print()

    print("top-20 hardest n by minimal d:")
    for row in hardest:
        print(
            f"  n={row['n']}, d={row['d']}, pair=({row['a']}, {row['b']}), "
            f"x={row['x']}, y={row['y']}, z={row['z']}"
        )


def generate_safe_rules(modulus: int, max_d: int) -> list[Rule]:
    divisor_set = set(divisors(modulus))
    rules: list[Rule] = []
    for d in range(3, max_d + 1, 4):
        pair_sum = 4 * d
        for a in divisor_set:
            if a > pair_sum // 2:
                continue
            b = pair_sum - a
            if b in divisor_set and lcm_many(24, 4, a, b) <= modulus and modulus % lcm_many(24, 4, a, b) == 0:
                rules.append(Rule(d, a, b))
    return sorted(rules, key=lambda rule: (rule.d, rule.a, rule.b))


def rule_covers_residue(rule: Rule, residue: int, modulus: int) -> bool:
    if modulus % rule.rule_modulus != 0:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def residues_1_mod_24(modulus: int) -> list[int]:
    return [residue for residue in range(1, modulus, 24)]


def cover_modulus(modulus: int, max_d: int) -> tuple[dict[int, Rule], list[int], list[Rule]]:
    rules = generate_safe_rules(modulus, max_d)
    assignments: dict[int, Rule] = {}
    uncovered: list[int] = []

    for residue in residues_1_mod_24(modulus):
        rule = next((candidate for candidate in rules if rule_covers_residue(candidate, residue, modulus)), None)
        if rule is None:
            uncovered.append(residue)
        else:
            assignments[residue] = rule
    return assignments, uncovered, rules


def modulus_search(args: argparse.Namespace) -> None:
    print("single-prime modulus search for n == 1 mod 24")
    print("p | modulus | subclasses | covered | uncovered")
    print("- | ------- | ---------- | ------- | ---------")
    best: tuple[int, int, int] | None = None
    for prime in PRIMES_TO_TEST:
        modulus = 24 * prime
        assignments, uncovered, _ = cover_modulus(modulus, args.max_d)
        total = modulus // 24
        covered = len(assignments)
        print(f"{prime} | {modulus} | {total} | {covered} | {len(uncovered)}")
        if best is None or covered > best[2]:
            best = (prime, modulus, covered)

    if best is not None:
        print()
        print(f"best single prime by covered count: p={best[0]}, modulus={best[1]}, covered={best[2]}")

    print()
    print("multi-prime modulus search")
    print("primes | modulus | subclasses | covered | uncovered | status")
    print("------ | ------- | ---------- | ------- | --------- | ------")
    for primes in MULTI_PRIME_PREFIXES:
        modulus = 24 * math.prod(primes)
        subclasses = modulus // 24
        if subclasses > args.residue_limit:
            print(
                f"{'*'.join(str(p) for p in primes)} | {modulus} | {subclasses} | "
                f"not_run | not_run | stopped: residue limit {args.residue_limit}"
            )
            break

        assignments, uncovered, _ = cover_modulus(modulus, args.max_d)
        print(
            f"{'*'.join(str(p) for p in primes)} | {modulus} | {subclasses} | "
            f"{len(assignments)} | {len(uncovered)} | ok"
        )
        if uncovered:
            print(f"  first uncovered: {uncovered[:40]}")


def greedy_cover(args: argparse.Namespace) -> None:
    global_modulus = args.global_modulus
    if global_modulus % 24 != 0:
        raise SystemExit("--global-modulus must be divisible by 24")

    target = set(residues_1_mod_24(global_modulus))
    rules = generate_safe_rules(global_modulus, args.max_d)
    rule_cover: dict[Rule, set[int]] = {}
    for rule in rules:
        covered = {residue for residue in target if rule_covers_residue(rule, residue, global_modulus)}
        if covered:
            rule_cover[rule] = covered

    uncovered = set(target)
    selected: list[Rule] = []
    while uncovered and len(selected) < args.greedy_limit:
        best_rule: Rule | None = None
        best_new: set[int] = set()
        for rule, covered in rule_cover.items():
            new = covered & uncovered
            if len(new) > len(best_new):
                best_rule = rule
                best_new = new
        if best_rule is None or not best_new:
            break
        selected.append(best_rule)
        uncovered -= best_new

    covered_count = len(target) - len(uncovered)
    print("greedy cover inside n == 1 mod 24")
    print(f"GLOBAL modulus: {global_modulus}")
    print(f"candidate rules: {len(rules)}")
    print(f"target residues: {len(target)}")
    print(f"covered residues: {covered_count}")
    print(f"uncovered residues: {len(uncovered)}")
    print()

    print("selected rules:")
    for rule in selected:
        print(
            f"  d={rule.d}, a={rule.a}, b={rule.b}, "
            f"rule_modulus={rule.rule_modulus}, newly safe modulo GLOBAL"
        )
    print()

    print("uncovered residues:")
    uncovered_list = sorted(uncovered)
    print(uncovered_list[:200])
    if len(uncovered_list) > 200:
        print(f"... {len(uncovered_list) - 200} more")

    uncovered_path = Path(f"uncovered_1_mod_24_global_{global_modulus}.csv")
    with uncovered_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["residue", "modulus"])
        writer.writeheader()
        for residue in uncovered_list:
            writer.writerow({"residue": residue, "modulus": global_modulus})
    print()
    print(f"uncovered residues written: {uncovered_path}")

    if not uncovered:
        path = Path("candidate_cover_1_mod_24.md")
        lines = [
            "# Candidate Cover For n == 1 mod 24",
            "",
            "This is a computer-found candidate cover for the subproblem `n == 1 mod 24`.",
            "It is not a proof of the full Erdos-Straus conjecture.",
            "",
            f"GLOBAL modulus: `{global_modulus}`",
            f"Max d searched: `{args.max_d}`",
            "",
            "| d | a | b | rule_modulus |",
            "| - | - | - | ------------ |",
        ]
        for rule in selected:
            lines.append(f"| {rule.d} | {rule.a} | {rule.b} | {rule.rule_modulus} |")
        lines += [
            "",
            "All residues `r mod GLOBAL` with `r == 1 mod 24` were covered by these rules.",
            "This candidate subproof should be independently checked mathematically.",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print()
        print(f"candidate cover for the n == 1 mod 24 subproblem generated: {path}")
        print("verdict: candidate subproof found")
    else:
        print()
        print("candidate cover file: not generated")
        print("verdict: not proved yet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Focused attack on n == 1 mod 24.")
    parser.add_argument("--max-n", type=int, default=500_000)
    parser.add_argument("--max-d", type=int, default=5000)
    parser.add_argument("--output", default="attack_1_mod_24_results.csv")
    parser.add_argument("--modulus-search", action="store_true")
    parser.add_argument("--greedy-cover", action="store_true")
    parser.add_argument("--global-modulus", type=int, default=DEFAULT_GLOBAL_MODULUS)
    parser.add_argument("--residue-limit", type=int, default=200_000)
    parser.add_argument("--greedy-limit", type=int, default=100)
    parser.add_argument("--reduce-by-divisors", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_d < 1:
        raise SystemExit("--max-d must be positive")
    if args.modulus_search:
        modulus_search(args)
    elif args.greedy_cover:
        greedy_cover(args)
    else:
        sample_scan(args)


if __name__ == "__main__":
    main()
