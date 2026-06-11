#!/usr/bin/env python3
"""Diagnose unresolved leaves from focused recursive cover runs.

This script does not try to prove anything. It explains why the current
recursive lift-cover search got stuck, and looks for symbolic groupings that
could replace explicit subresidue enumeration.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Iterable

from recursive_core_cover import (
    BASE_MODULUS,
    Rule,
    lcm_many,
    rule_covers_class,
    solution_from_rule,
)


DEFAULT_FOCUS_RESIDUES = [289, 361, 529, 841, 961]
DIAGNOSTICS_PATH = Path("recursive_failure_diagnostics.csv")
GROUPS_PATH = Path("recursive_failure_symbolic_groups.csv")
META_PATH = Path("recursive_failure_diagnostics_meta.csv")


def factorization(value: int) -> tuple[tuple[int, int], ...]:
    factors: list[tuple[int, int]] = []
    n = value
    power = 0
    while n % 2 == 0:
        n //= 2
        power += 1
    if power:
        factors.append((2, power))

    divisor = 3
    while divisor * divisor <= n:
        power = 0
        while n % divisor == 0:
            n //= divisor
            power += 1
        if power:
            factors.append((divisor, power))
        divisor += 2

    if n > 1:
        factors.append((n, 1))
    return tuple(factors)


def format_factorization(factors: tuple[tuple[int, int], ...]) -> str:
    if not factors:
        return "1"
    parts = []
    for prime, power in factors:
        parts.append(str(prime) if power == 1 else f"{prime}^{power}")
    return "*".join(parts)


def unique_prime_factors(value: int) -> list[int]:
    return [prime for prime, _ in factorization(value)]


def input_paths(focus_r: int) -> tuple[Path, Path, Path]:
    return (
        Path(f"recursive_focus_{focus_r}_classes.csv"),
        Path(f"recursive_focus_{focus_r}_rules.csv"),
        Path(f"recursive_focus_{focus_r}_unresolved.csv"),
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def sample_n(modulus: int, residue: int) -> int:
    return residue if residue > 1 else residue + modulus


def find_minimal_rule_with_budget(
    n: int,
    max_d: int,
    max_pair_checks: int,
) -> tuple[Rule | None, str]:
    pair_checks = 0
    first_d = (-n) % 4
    first_d = first_d if first_d > 0 else 4

    for d in range(first_d, max_d + 1, 4):
        product = n * (n + d)
        pair_sum = 4 * d
        for a in range(1, pair_sum // 2 + 1):
            pair_checks += 1
            if max_pair_checks and pair_checks > max_pair_checks:
                return None, "search_budget_exceeded_before_max_d"
            b = pair_sum - a
            if product % a == 0 and product % b == 0:
                return Rule(d, a, b), "found"
    return None, "no_rule_found_up_to_max_d"


def diagnose_reason(
    modulus: int,
    residue: int,
    rule: Rule | None,
    max_modulus: int,
    max_subresidues_per_node: int,
) -> tuple[int | None, str]:
    if rule is None:
        return None, "no_rule_found_up_to_max_d"

    rule_modulus = rule.rule_modulus
    needed_lift = lcm_many(modulus, rule_modulus)
    if modulus % rule_modulus == 0:
        if rule_covers_class(modulus, residue, rule):
            return needed_lift, "sample_rule_already_covers_class"
        return needed_lift, "rule_modulus_already_divides_m_but_rule_still_fails"
    if needed_lift > max_modulus:
        return needed_lift, "needed_lift_exceeds_max_modulus"
    if needed_lift // modulus > max_subresidues_per_node:
        return needed_lift, "needed_lift_creates_too_many_subresidues"
    return needed_lift, "rule_covers_only_partial_subclasses_after_lift"


def diagnose_leaf(task: tuple[int, int, int, int, int, int, int, int]) -> dict[str, object]:
    focus_r, depth, modulus, residue, max_d, max_modulus, max_subresidues, max_pair_checks = task
    n = sample_n(modulus, residue)
    rule, search_status = find_minimal_rule_with_budget(n, max_d, max_pair_checks)
    if search_status != "found":
        reason = search_status
        return {
            "focus_r": focus_r,
            "depth": depth,
            "modulus": modulus,
            "residue": residue,
            "sample_n": n,
            "d": "",
            "a": "",
            "b": "",
            "rule_modulus": "",
            "needed_lift": "",
            "reason": reason,
        }

    needed_lift, reason = diagnose_reason(
        modulus,
        residue,
        rule,
        max_modulus,
        max_subresidues,
    )

    # Compute x, y, z once to make sure the sample rule is algebraically usable.
    # The CSV schema intentionally stays focused on rule diagnostics.
    if solution_from_rule(n, rule) is None:
        reason = "sample_rule_failed_to_build_solution"

    return {
        "focus_r": focus_r,
        "depth": depth,
        "modulus": modulus,
        "residue": residue,
        "sample_n": n,
        "d": rule.d,
        "a": rule.a,
        "b": rule.b,
        "rule_modulus": rule.rule_modulus,
        "needed_lift": "" if needed_lift is None else needed_lift,
        "reason": reason,
    }


def iter_unresolved_tasks(
    focus_residues: list[int],
    max_d: int,
    max_modulus: int,
    max_subresidues: int,
    max_pair_checks: int,
) -> Iterable[tuple[int, int, int, int, int, int, int, int]]:
    for focus_r in focus_residues:
        _, _, unresolved_path = input_paths(focus_r)
        with unresolved_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                yield (
                    focus_r,
                    int(row["depth"]),
                    int(row["modulus"]),
                    int(row["residue"]),
                    max_d,
                    max_modulus,
                    max_subresidues,
                    max_pair_checks,
                )


def write_meta(args: argparse.Namespace, focus_residues: list[int]) -> None:
    with META_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "max_d",
                "max_modulus",
                "max_subresidues_per_node",
                "max_pair_checks",
                "focus_residues",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "max_d": args.max_d,
                "max_modulus": args.max_modulus,
                "max_subresidues_per_node": args.max_subresidues_per_node,
                "max_pair_checks": args.max_pair_checks,
                "focus_residues": ",".join(str(r) for r in focus_residues),
            }
        )


def meta_matches(args: argparse.Namespace, focus_residues: list[int]) -> bool:
    if not META_PATH.exists() or not DIAGNOSTICS_PATH.exists():
        return False
    with META_PATH.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        return False
    row = rows[0]
    return (
        row["max_d"] == str(args.max_d)
        and row["max_modulus"] == str(args.max_modulus)
        and row["max_subresidues_per_node"] == str(args.max_subresidues_per_node)
        and row.get("max_pair_checks", "") == str(args.max_pair_checks)
        and row["focus_residues"] == ",".join(str(r) for r in focus_residues)
    )


def generate_diagnostics(args: argparse.Namespace, focus_residues: list[int]) -> None:
    total = sum(1 for _ in iter_unresolved_tasks(
        focus_residues,
        args.max_d,
        args.max_modulus,
        args.max_subresidues_per_node,
        args.max_pair_checks,
    ))
    print(f"diagnosing unresolved leaves: {total}")

    fieldnames = [
        "focus_r",
        "depth",
        "modulus",
        "residue",
        "sample_n",
        "d",
        "a",
        "b",
        "rule_modulus",
        "needed_lift",
        "reason",
    ]
    tasks = iter_unresolved_tasks(
        focus_residues,
        args.max_d,
        args.max_modulus,
        args.max_subresidues_per_node,
        args.max_pair_checks,
    )

    processed = 0
    with DIAGNOSTICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        if args.workers <= 1:
            for result in map(diagnose_leaf, tasks):
                writer.writerow(result)
                processed += 1
                if args.progress_interval and processed % args.progress_interval == 0:
                    print(f"  processed {processed}/{total}")
        else:
            with Pool(processes=args.workers) as pool:
                for result in pool.imap_unordered(diagnose_leaf, tasks, chunksize=args.chunksize):
                    writer.writerow(result)
                    processed += 1
                    if args.progress_interval and processed % args.progress_interval == 0:
                        print(f"  processed {processed}/{total}")

    write_meta(args, focus_residues)


def read_diagnostics() -> list[dict[str, str]]:
    return read_csv(DIAGNOSTICS_PATH)


def summarize_inputs(focus_residues: list[int]) -> None:
    print("input summaries:")
    for focus_r in focus_residues:
        classes_path, rules_path, unresolved_path = input_paths(focus_r)
        classes = read_csv(classes_path)
        rules = read_csv(rules_path)
        unresolved = read_csv(unresolved_path)
        depth_counts = Counter(int(row["depth"]) for row in unresolved)
        reason_counts = Counter(row["reason"].split(" ")[0] for row in unresolved)
        modulus_counts = Counter(int(row["modulus"]) for row in unresolved)
        selected_d = Counter(int(row["d"]) for row in rules if row["d"])

        print(f"\nfocus r={focus_r}")
        print(f"  total unresolved leaves: {len(unresolved)}")
        print(f"  class records: {len(classes)}")
        print(f"  selected rule records: {len(rules)}")
        print(f"  depth distribution: {depth_counts.most_common()}")
        print(f"  reason distribution: {reason_counts.most_common(10)}")
        print(f"  top modulus values: {modulus_counts.most_common(20)}")
        print(f"  previous selected-rule d top: {selected_d.most_common(10)}")


def build_symbolic_groups(rows: list[dict[str, str]]) -> tuple[Counter, dict[tuple, dict[str, object]]]:
    modulus_factor_cache: dict[int, str] = {}
    ratio_factor_cache: dict[int, str] = {}
    groups: Counter = Counter()
    examples: dict[tuple, dict[str, object]] = {}

    with GROUPS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "focus_r",
                "modulus_factorization",
                "missing_prime",
                "d",
                "a",
                "b",
                "rule_modulus",
                "lift_ratio",
                "lift_ratio_factorization",
                "count",
                "example_modulus",
                "example_residue",
            ],
        )
        writer.writeheader()

        for row in rows:
            if not row["d"] or not row["needed_lift"]:
                continue
            focus_r = int(row["focus_r"])
            modulus = int(row["modulus"])
            residue = int(row["residue"])
            rule_modulus = int(row["rule_modulus"])
            needed_lift = int(row["needed_lift"])
            ratio = needed_lift // modulus
            missing_factor = rule_modulus // math.gcd(modulus, rule_modulus)
            missing_primes = unique_prime_factors(missing_factor) or [1]

            if modulus not in modulus_factor_cache:
                modulus_factor_cache[modulus] = format_factorization(factorization(modulus))
            if ratio not in ratio_factor_cache:
                ratio_factor_cache[ratio] = format_factorization(factorization(ratio))

            for prime in missing_primes:
                key = (
                    focus_r,
                    modulus_factor_cache[modulus],
                    prime,
                    int(row["d"]),
                    int(row["a"]),
                    int(row["b"]),
                    rule_modulus,
                    ratio,
                    ratio_factor_cache[ratio],
                )
                groups[key] += 1
                examples.setdefault(
                    key,
                    {
                        "modulus": modulus,
                        "residue": residue,
                    },
                )

        for key, count in groups.most_common():
            (
                focus_r,
                modulus_factorization,
                missing_prime,
                d,
                a,
                b,
                rule_modulus,
                ratio,
                ratio_factorization,
            ) = key
            example = examples[key]
            writer.writerow(
                {
                    "focus_r": focus_r,
                    "modulus_factorization": modulus_factorization,
                    "missing_prime": missing_prime,
                    "d": d,
                    "a": a,
                    "b": b,
                    "rule_modulus": rule_modulus,
                    "lift_ratio": ratio,
                    "lift_ratio_factorization": ratio_factorization,
                    "count": count,
                    "example_modulus": example["modulus"],
                    "example_residue": example["residue"],
                }
            )

    return groups, examples


def summarize_diagnostics(rows: list[dict[str, str]], focus_residues: list[int]) -> None:
    print("\ndiagnostic summaries:")
    by_focus: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_focus[int(row["focus_r"])].append(row)

    for focus_r in focus_residues:
        focus_rows = by_focus[focus_r]
        reason_counts = Counter(row["reason"] for row in focus_rows)
        depth_counts = Counter(int(row["depth"]) for row in focus_rows)
        modulus_counts = Counter(int(row["modulus"]) for row in focus_rows)
        d_counts = Counter(int(row["d"]) for row in focus_rows if row["d"])
        pair_counts = Counter((int(row["a"]), int(row["b"])) for row in focus_rows if row["a"])
        missing_prime_counts: Counter[int] = Counter()
        ratio_counts: Counter[int] = Counter()

        for row in focus_rows:
            if not row["rule_modulus"]:
                continue
            modulus = int(row["modulus"])
            rule_modulus = int(row["rule_modulus"])
            needed_lift = int(row["needed_lift"])
            ratio = needed_lift // modulus
            ratio_counts[ratio] += 1
            missing_factor = rule_modulus // math.gcd(modulus, rule_modulus)
            for prime in unique_prime_factors(missing_factor):
                missing_prime_counts[prime] += 1

        print(f"\nfocus r={focus_r}")
        print(f"  total diagnostic rows: {len(focus_rows)}")
        print(f"  depth distribution: {depth_counts.most_common()}")
        print(f"  reasons: {reason_counts.most_common(20)}")
        print(f"  top 20 modulus values: {modulus_counts.most_common(20)}")
        print(f"  top 20 missing prime factors: {missing_prime_counts.most_common(20)}")
        print(f"  top 20 minimal d: {d_counts.most_common(20)}")
        print(f"  top 20 pairs: {pair_counts.most_common(20)}")
        print(f"  top 20 lift ratios: {ratio_counts.most_common(20)}")


def print_symbolic_groups(groups: Counter, examples: dict[tuple, dict[str, object]]) -> None:
    print("\nsymbolic compression candidates:")
    for key, count in groups.most_common(30):
        (
            focus_r,
            modulus_factorization,
            missing_prime,
            d,
            a,
            b,
            rule_modulus,
            ratio,
            ratio_factorization,
        ) = key
        example = examples[key]
        print(
            f"  focus r={focus_r}: {count} leaves need lift ratio {ratio} "
            f"({ratio_factorization}), missing prime {missing_prime}, "
            f"d={d}, pair=({a},{b}), rule_modulus={rule_modulus}; "
            f"example class mod={example['modulus']} residue={example['residue']}"
        )
        print(f"    current modulus factors: {modulus_factorization}")


def recommendations(rows: list[dict[str, str]], focus_residues: list[int]) -> None:
    print("\nbranch strategy recommendations:")
    by_focus: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_focus[int(row["focus_r"])].append(row)

    for focus_r in focus_residues:
        focus_rows = by_focus[focus_r]
        reason_counts = Counter(row["reason"] for row in focus_rows)
        missing_prime_counts: Counter[int] = Counter()
        d_counts = Counter(int(row["d"]) for row in focus_rows if row["d"])
        pair_counts = Counter((int(row["a"]), int(row["b"])) for row in focus_rows if row["a"])

        for row in focus_rows:
            if not row["rule_modulus"]:
                continue
            modulus = int(row["modulus"])
            rule_modulus = int(row["rule_modulus"])
            missing_factor = rule_modulus // math.gcd(modulus, rule_modulus)
            for prime in unique_prime_factors(missing_factor):
                missing_prime_counts[prime] += 1

        dominant_reason = reason_counts.most_common(1)[0][0] if reason_counts else "unknown"
        top_primes = [prime for prime, _ in missing_prime_counts.most_common(5)]
        top_d = [d for d, _ in d_counts.most_common(5)]
        top_pairs = [pair for pair, _ in pair_counts.most_common(5)]

        print(f"  focus r={focus_r}:")
        if dominant_reason == "needed_lift_exceeds_max_modulus":
            print(
                "    next: do not just raise max_modulus globally; lift by one "
                f"dominant missing prime at a time, especially {top_primes}."
            )
        elif dominant_reason == "needed_lift_creates_too_many_subresidues":
            print(
                "    next: avoid explicit sibling enumeration; use symbolic split "
                "conditions for the dominant lift ratios."
            )
        else:
            print(
                f"    next: inspect dominant reason `{dominant_reason}` with a targeted branch run."
            )
        print(f"    dominant d values: {top_d}")
        print(f"    dominant pairs: {top_pairs}")
        print(
            "    likely useful: symbolic split instead of explicit subresidue enumeration; "
            "a square-like residue lemma is still plausible but not established."
        )


def select_focus_leaf(rows: list[dict[str, str]]) -> dict[str, str] | None:
    groups: Counter = Counter()
    examples: dict[tuple, dict[str, str]] = {}
    for row in rows:
        if not row["d"] or not row["needed_lift"]:
            continue
        modulus = int(row["modulus"])
        rule_modulus = int(row["rule_modulus"])
        needed_lift = int(row["needed_lift"])
        ratio = needed_lift // modulus
        missing_factor = rule_modulus // math.gcd(modulus, rule_modulus)
        missing_primes = tuple(unique_prime_factors(missing_factor))
        key = (
            int(row["focus_r"]),
            missing_primes,
            int(row["d"]),
            int(row["a"]),
            int(row["b"]),
            rule_modulus,
            ratio,
        )
        groups[key] += 1
        examples.setdefault(key, row)
    if not groups:
        return None
    return examples[groups.most_common(1)[0][0]]


def find_first_uncovered_subresidue(
    modulus: int,
    residue: int,
    refined_modulus: int,
    rule: Rule,
    scan_limit: int,
) -> int | None:
    ratio = refined_modulus // modulus
    for k in range(min(ratio, scan_limit)):
        candidate = residue + k * modulus
        if not rule_covers_class(refined_modulus, candidate, rule):
            return candidate
    return None


def focus_leaf_deep_dive(args: argparse.Namespace, rows: list[dict[str, str]]) -> None:
    start = select_focus_leaf(rows)
    print("\nfocus-leaf deep dive:")
    if start is None:
        print("  no suitable diagnostic row found")
        return

    focus_r = int(start["focus_r"])
    modulus = int(start["modulus"])
    residue = int(start["residue"])
    print(
        f"  starting from focus r={focus_r}, depth={start['depth']}, "
        f"modulus={modulus}, residue={residue}"
    )

    for step in range(args.leaf_depth):
        n = sample_n(modulus, residue)
        rule, search_status = find_minimal_rule_with_budget(
            n,
            args.max_d,
            args.leaf_max_pair_checks,
        )
        if rule is None:
            print(f"  step {step}: {search_status} for sample n={n}")
            return

        needed_lift = lcm_many(modulus, rule.rule_modulus)
        ratio = needed_lift // modulus
        reason = diagnose_reason(
            modulus,
            residue,
            rule,
            args.leaf_max_modulus,
            args.leaf_max_subresidues,
        )[1]
        print(
            f"  step {step}: modulus={modulus}, residue={residue}, sample_n={n}, "
            f"d={rule.d}, pair=({rule.a},{rule.b}), rule_modulus={rule.rule_modulus}, "
            f"needed_lift={needed_lift}, ratio={ratio}, reason={reason}"
        )

        if rule_covers_class(modulus, residue, rule):
            print("    branch class is covered by this rule")
            return
        if needed_lift > args.leaf_max_modulus:
            print("    stop: needed lift exceeds leaf_max_modulus")
            return
        if ratio > args.leaf_max_subresidues:
            print("    stop: ratio exceeds leaf_max_subresidues")
            return

        next_residue = find_first_uncovered_subresidue(
            modulus,
            residue,
            needed_lift,
            rule,
            args.leaf_scan_limit,
        )
        if next_residue is None:
            print(
                "    no uncovered sibling found within scan limit; "
                "this pattern wants symbolic coverage accounting"
            )
            return
        modulus = needed_lift
        residue = next_residue

    print("  stop: leaf_depth reached without closing the branch")


def parse_focus_residues(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_FOCUS_RESIDUES
    return [int(part) for part in raw.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze recursive cover unresolved leaves.")
    parser.add_argument("--max-d", type=int, default=50_000)
    parser.add_argument("--max-modulus", type=int, default=1_000_000_000_000)
    parser.add_argument("--max-subresidues-per-node", type=int, default=5_000)
    parser.add_argument("--focus-residues", help="Comma-separated focus residues to analyze.")
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--chunksize", type=int, default=1)
    parser.add_argument("--progress-interval", type=int, default=25_000)
    parser.add_argument(
        "--max-pair-checks",
        type=int,
        default=2_000_000,
        help="0 means exact scan to max-d; positive values mark hard leaves as search_budget_exceeded.",
    )
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--focus-leaf", action="store_true")
    parser.add_argument("--leaf-depth", type=int, default=8)
    parser.add_argument("--leaf-max-modulus", type=int, default=10_000_000_000_000_000)
    parser.add_argument("--leaf-max-subresidues", type=int, default=200_000)
    parser.add_argument("--leaf-scan-limit", type=int, default=200_000)
    parser.add_argument("--leaf-max-pair-checks", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    focus_residues = parse_focus_residues(args.focus_residues)
    summarize_inputs(focus_residues)

    if args.recompute or not meta_matches(args, focus_residues):
        generate_diagnostics(args, focus_residues)
    else:
        print(f"\nreusing existing diagnostics: {DIAGNOSTICS_PATH}")

    rows = read_diagnostics()
    summarize_diagnostics(rows, focus_residues)
    groups, examples = build_symbolic_groups(rows)
    print_symbolic_groups(groups, examples)
    recommendations(rows, focus_residues)

    if args.focus_leaf:
        focus_leaf_deep_dive(args, rows)

    print("\nverdict: not proved yet")


if __name__ == "__main__":
    main()
