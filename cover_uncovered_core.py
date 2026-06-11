#!/usr/bin/env python3
"""Recursive/local lifted cover for the 330-core modulo 120120.

This is a local research tool.  It can generate a candidate cover for the
previously uncovered core, but it never writes a proof certificate for the
full conjecture.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from attack_1_mod_24 import DEFAULT_GLOBAL_MODULUS, cover_modulus
from erdos_straus import check_solution, first_compatible_d


BASE_MODULUS = DEFAULT_GLOBAL_MODULUS
UNCOVERED_PATH = Path(f"uncovered_1_mod_24_global_{BASE_MODULUS}.csv")


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def rule_modulus(self) -> int:
        return lcm_many(4, self.a, self.b)


@dataclass
class SelectedRule:
    rule: Rule
    covered: set[int]


@dataclass
class LocalResult:
    r: int
    B: int
    M: int
    total_subresidues: int
    covered: int
    uncovered: set[int]
    success: bool
    selected: list[SelectedRule]
    warnings: list[str]


@dataclass
class CoverEvaluation:
    selected: list[SelectedRule]
    uncovered: set[int]
    expansion_rules: dict[int, Rule]


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


def solution_from_rule(n: int, rule: Rule) -> tuple[int, int, int]:
    x = (n + rule.d) // 4
    product = n * (n + rule.d)
    return x, product // rule.a, product // rule.b


def find_minimal_rule(n: int, max_d: int) -> Rule | None:
    for d in range(first_compatible_d(n), max_d + 1, 4):
        product = n * (n + d)
        pair_sum = 4 * d
        for a in range(1, pair_sum // 2 + 1):
            b = pair_sum - a
            if product % a == 0 and product % b == 0:
                return Rule(d, a, b)
    return None


def cached_minimal_rule(
    n: int,
    max_d: int,
    sample_rule_cache: dict[tuple[int, int], Rule | None],
) -> Rule | None:
    key = (n, max_d)
    if key not in sample_rule_cache:
        sample_rule_cache[key] = find_minimal_rule(n, max_d)
    return sample_rule_cache[key]


def load_uncovered(max_d: int) -> list[int]:
    if not UNCOVERED_PATH.exists():
        _, uncovered, _ = cover_modulus(BASE_MODULUS, max_d)
        with UNCOVERED_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["residue", "modulus"])
            writer.writeheader()
            for residue in uncovered:
                writer.writerow({"residue": residue, "modulus": BASE_MODULUS})

    residues: list[int] = []
    with UNCOVERED_PATH.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if int(row["modulus"]) != BASE_MODULUS:
                raise ValueError(f"unexpected modulus in {UNCOVERED_PATH}: {row['modulus']}")
            residues.append(int(row["residue"]))
    return residues


def subresidues(r: int, B: int, M: int) -> list[int]:
    if M % B != 0:
        raise ValueError("M must be a multiple of B")
    return [r + k * B for k in range(M // B)]


def rule_covers_residue(rule: Rule, R: int, M: int) -> bool:
    if M % rule.rule_modulus != 0:
        return False
    if (R + rule.d) % 4 != 0:
        return False
    product = R * (R + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def find_safe_rules_for_residue(
    R: int,
    M: int,
    max_d: int,
    divisor_values: list[int],
    divisor_set: set[int],
    limit: int,
) -> list[Rule]:
    """Find a few rules that are safe for the whole class R modulo M."""
    rules: list[Rule] = []

    for d in range(first_compatible_d(R), max_d + 1, 4):
        product = R * (R + d)
        pair_sum = 4 * d
        for a in divisor_values:
            if a > pair_sum // 2:
                break
            if product % a != 0:
                continue
            b = pair_sum - a
            if b not in divisor_set:
                continue
            if product % b != 0:
                continue
            rule = Rule(d, a, b)
            if M % rule.rule_modulus == 0:
                rules.append(rule)
                if len(rules) >= limit:
                    return rules
    return rules


def greedy_local_cover(
    r: int,
    B: int,
    M: int,
    max_d: int,
    rules_per_subresidue: int,
) -> tuple[list[SelectedRule], set[int]]:
    targets = set(subresidues(r, B, M))
    divisor_values = divisors(M)
    divisor_set = set(divisor_values)
    rules: set[Rule] = set()

    for R in targets:
        local_rules = find_safe_rules_for_residue(
            R,
            M,
            max_d,
            divisor_values,
            divisor_set,
            rules_per_subresidue,
        )
        if local_rules:
            rules.update(local_rules)

    rule_cover: dict[Rule, set[int]] = {}

    for rule in rules:
        covered = {R for R in targets if rule_covers_residue(rule, R, M)}
        if covered:
            rule_cover[rule] = covered

    uncovered = set(targets)
    selected: list[SelectedRule] = []

    while uncovered:
        best_rule: Rule | None = None
        best_new: set[int] = set()
        for rule, covered in rule_cover.items():
            new = covered & uncovered
            if len(new) > len(best_new):
                best_rule = rule
                best_new = new
        if best_rule is None or not best_new:
            break
        selected.append(SelectedRule(best_rule, set(best_new)))
        uncovered -= best_new

    return selected, uncovered


def evaluate_local_cover(
    r: int,
    B: int,
    M: int,
    max_d: int,
    seed_rules: set[Rule],
    sample_rule_cache: dict[tuple[int, int], Rule | None],
    expansion_sample_limit: int,
) -> CoverEvaluation:
    """Build a local greedy cover from known local seed rules.

    This is deliberately narrower than a full exhaustive rule search. It keeps
    the local lift diagnostic fast enough to run over all 330 core residues.
    A selected rule is still accepted only when it is residue-safe modulo M.
    """
    targets = set(subresidues(r, B, M))
    rule_cover: dict[Rule, set[int]] = {}
    for rule in seed_rules:
        covered = {R for R in targets if rule_covers_residue(rule, R, M)}
        if covered:
            rule_cover[rule] = covered

    uncovered = set(targets)
    selected: list[SelectedRule] = []

    while uncovered:
        best_rule: Rule | None = None
        best_new: set[int] = set()
        for rule, covered in rule_cover.items():
            new = covered & uncovered
            if len(new) > len(best_new):
                best_rule = rule
                best_new = new
        if best_rule is None or not best_new:
            break
        selected.append(SelectedRule(best_rule, set(best_new)))
        uncovered -= best_new

    expansion_rules: dict[int, Rule] = {}
    sampled_uncovered = sorted(uncovered)[:expansion_sample_limit]
    for R in sampled_uncovered:
        n = R if R > 1 else R + M
        sample_rule = cached_minimal_rule(n, max_d, sample_rule_cache)
        if sample_rule is not None:
            expansion_rules[R] = sample_rule

    return CoverEvaluation(selected=selected, uncovered=uncovered, expansion_rules=expansion_rules)


def evaluate_and_record(
    r: int,
    B: int,
    M: int,
    args: argparse.Namespace,
    warnings: list[str],
    cover_cache: dict[tuple[int, int, int, tuple[tuple[int, int, int], ...]], CoverEvaluation],
    seed_rules: set[Rule],
    sample_rule_cache: dict[tuple[int, int], Rule | None],
) -> LocalResult:
    seed_key = tuple(sorted((rule.d, rule.a, rule.b) for rule in seed_rules))
    cache_key = (r, M, args.max_d, seed_key)
    if cache_key not in cover_cache:
        cover_cache[cache_key] = evaluate_local_cover(
            r,
            B,
            M,
            args.max_d,
            seed_rules,
            sample_rule_cache,
            args.expansion_sample_limit,
        )
    evaluation = cover_cache[cache_key]
    total = M // B
    return LocalResult(
        r=r,
        B=B,
        M=M,
        total_subresidues=total,
        covered=total - len(evaluation.uncovered),
        uncovered=set(evaluation.uncovered),
        success=not evaluation.uncovered,
        selected=evaluation.selected,
        warnings=list(warnings),
    )


def get_cached_evaluation(
    r: int,
    M: int,
    max_d: int,
    seed_rules: set[Rule],
    cover_cache: dict[tuple[int, int, int, tuple[tuple[int, int, int], ...]], CoverEvaluation],
) -> CoverEvaluation:
    seed_key = tuple(sorted((rule.d, rule.a, rule.b) for rule in seed_rules))
    return cover_cache[(r, M, max_d, seed_key)]


def choose_next_modulus_from_uncovered(
    M: int,
    B: int,
    uncovered: set[int],
    expansion_rules: dict[int, Rule],
    args: argparse.Namespace,
    warnings: list[str],
) -> int | None:
    """Pick the most useful missing rule modulus that still respects limits."""
    candidates: Counter[int] = Counter()
    for R in uncovered:
        rule = expansion_rules.get(R)
        if rule is None:
            continue
        next_M = lcm_many(M, rule.rule_modulus)
        if next_M == M:
            continue
        multiplier = next_M // B
        if multiplier > args.max_local_multiplier or multiplier > args.max_subresidues:
            continue
        candidates[rule.rule_modulus] += 1

    if not candidates:
        warnings.append("no limit-safe modulus expansion found from uncovered subresidues")
        return None

    def score(rule_modulus: int) -> tuple[int, int]:
        next_M = lcm_many(M, rule_modulus)
        growth = next_M // M
        return candidates[rule_modulus], -growth

    best_modulus = max(candidates, key=score)
    return lcm_many(M, best_modulus)


def local_cover_for_residue(
    r: int,
    args: argparse.Namespace,
    cover_cache: dict[tuple[int, int, int, tuple[tuple[int, int, int], ...]], CoverEvaluation],
    sample_rule_cache: dict[tuple[int, int], Rule | None],
) -> LocalResult:
    B = BASE_MODULUS
    M = B
    warnings: list[str] = []
    tried_moduli: set[int] = set()
    best_result: LocalResult | None = None
    seed_rules: set[Rule] = set()

    for sample_index in range(args.discovery_samples):
        n = r + sample_index * B
        if n <= 1:
            n += B
        sample_rule = cached_minimal_rule(n, args.max_d, sample_rule_cache)
        if sample_rule is None:
            warnings.append(f"no sample rule for n={n}")
            continue
        seed_rules.add(sample_rule)

        candidate_M = lcm_many(M, sample_rule.rule_modulus)
        multiplier = candidate_M // B
        if multiplier > args.max_local_multiplier:
            warnings.append(
                f"skipped rule d={sample_rule.d},a={sample_rule.a},b={sample_rule.b}: "
                f"local multiplier {multiplier} exceeds {args.max_local_multiplier}"
            )
            continue
        if multiplier > args.max_subresidues:
            warnings.append(
                f"skipped rule d={sample_rule.d},a={sample_rule.a},b={sample_rule.b}: "
                f"subresidues {multiplier} exceeds {args.max_subresidues}"
            )
            continue

        M = candidate_M
        if M in tried_moduli:
            continue
        tried_moduli.add(M)

        result = evaluate_and_record(
            r,
            B,
            M,
            args,
            warnings,
            cover_cache,
            seed_rules,
            sample_rule_cache,
        )

        if best_result is None or result.covered > best_result.covered:
            best_result = result
        if result.success:
            return result

        for _ in range(args.local_expansion_rounds):
            next_M = choose_next_modulus_from_uncovered(
                M,
                B,
                result.uncovered,
                get_cached_evaluation(r, M, args.max_d, seed_rules, cover_cache).expansion_rules,
                args,
                warnings,
            )
            if next_M is None or next_M in tried_moduli:
                break
            for rule in get_cached_evaluation(
                r,
                M,
                args.max_d,
                seed_rules,
                cover_cache,
            ).expansion_rules.values():
                seed_rules.add(rule)
            M = next_M
            tried_moduli.add(M)
            result = evaluate_and_record(
                r,
                B,
                M,
                args,
                warnings,
                cover_cache,
                seed_rules,
                sample_rule_cache,
            )
            if best_result is None or result.covered > best_result.covered:
                best_result = result
            if result.success:
                return result

    if best_result is not None:
        return best_result

    return LocalResult(
        r=r,
        B=B,
        M=M,
        total_subresidues=M // B,
        covered=0,
        uncovered=set(subresidues(r, B, M)),
        success=False,
        selected=[],
        warnings=warnings or ["no usable local modulus discovered"],
    )


def validate_selected_rules(results: list[LocalResult]) -> list[str]:
    failures: list[str] = []
    for result in results:
        for selected in result.selected:
            rule = selected.rule
            for R in selected.covered:
                for k in range(3):
                    n = R + k * result.M
                    if n <= 1:
                        continue
                    if not rule_covers_residue(rule, R, result.M):
                        failures.append(
                            f"r={result.r}, R={R}, rule=({rule.d},{rule.a},{rule.b}) is not residue-safe"
                        )
                        continue
                    x, y, z = solution_from_rule(n, rule)
                    if not check_solution(n, x, y, z):
                        failures.append(
                            f"sample failed: r={result.r}, R={R}, n={n}, rule=({rule.d},{rule.a},{rule.b})"
                        )
    return failures


def write_outputs(results: list[LocalResult]) -> None:
    with Path("core_local_cover_summary.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "r",
                "B",
                "M",
                "total_subresidues",
                "covered",
                "uncovered",
                "success",
                "selected_rule_count",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "r": result.r,
                    "B": result.B,
                    "M": result.M,
                    "total_subresidues": result.total_subresidues,
                    "covered": result.covered,
                    "uncovered": len(result.uncovered),
                    "success": result.success,
                    "selected_rule_count": len(result.selected),
                }
            )

    with Path("core_local_cover_rules.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["r", "M", "d", "a", "b", "rule_modulus", "covered_count"],
        )
        writer.writeheader()
        for result in results:
            for selected in result.selected:
                rule = selected.rule
                writer.writerow(
                    {
                        "r": result.r,
                        "M": result.M,
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                        "rule_modulus": rule.rule_modulus,
                        "covered_count": len(selected.covered),
                    }
                )

    with Path("core_local_uncovered_subresidues.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["r", "M", "R"])
        writer.writeheader()
        for result in results:
            for R in sorted(result.uncovered):
                writer.writerow({"r": result.r, "M": result.M, "R": R})


def write_candidate_core_cover(results: list[LocalResult], max_d: int) -> Path:
    path = Path("candidate_cover_1_mod_24_core.md")
    lines = [
        "# Candidate Local Cover For The Previously Uncovered Core Modulo 120120",
        "",
        "This is a computer-found candidate local cover for the 330-core only.",
        "It is not a proof of the full Erdos-Straus conjecture.",
        "",
        f"Max d searched: `{max_d}`",
        "",
        "| r | M | d | a | b | rule_modulus | covered subresidues |",
        "| - | - | - | - | - | ------------ | ------------------- |",
    ]
    for result in results:
        for selected in result.selected:
            rule = selected.rule
            lines.append(
                f"| {result.r} | {result.M} | {rule.d} | {rule.a} | {rule.b} | "
                f"{rule.rule_modulus} | {len(selected.covered)} |"
            )
    lines += [
        "",
        "All 330 previously uncovered residues were locally covered by lifted subresidue classes.",
        "This candidate core cover should be independently checked mathematically.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local lifted cover for the 120120 core.")
    parser.add_argument("--max-d", type=int, default=5000)
    parser.add_argument("--max-local-multiplier", type=int, default=5000)
    parser.add_argument("--max-subresidues", type=int, default=20000)
    parser.add_argument("--discovery-samples", type=int, default=24)
    parser.add_argument("--local-expansion-rounds", type=int, default=8)
    parser.add_argument("--expansion-sample-limit", type=int, default=256)
    parser.add_argument("--rules-per-subresidue", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    residues = load_uncovered(args.max_d)
    cover_cache: dict[
        tuple[int, int, int, tuple[tuple[int, int, int], ...]],
        CoverEvaluation,
    ] = {}
    sample_rule_cache: dict[tuple[int, int], Rule | None] = {}
    results: list[LocalResult] = []

    for index, r in enumerate(residues, start=1):
        result = local_cover_for_residue(r, args, cover_cache, sample_rule_cache)
        results.append(result)
        print(
            f"{index:03d}/{len(residues)} r={r} M={result.M} "
            f"subres={result.total_subresidues} covered={result.covered} "
            f"uncovered={len(result.uncovered)} success={result.success} "
            f"rules={len(result.selected)}"
        )

    failures = validate_selected_rules(results)
    write_outputs(results)

    covered_results = [result for result in results if result.success]
    failed_results = [result for result in results if not result.success]
    all_selected = [selected.rule for result in results for selected in result.selected]
    d_counts = Counter(rule.d for rule in all_selected)
    pair_counts = Counter((rule.a, rule.b) for rule in all_selected)
    max_M = max((result.M for result in results), default=BASE_MODULUS)
    max_subresidues = max((result.total_subresidues for result in results), default=0)

    candidate_path: Path | None = None
    if not failed_results and not failures:
        candidate_path = write_candidate_core_cover(results, args.max_d)

    print()
    print("summary:")
    print(f"  total core residues: {len(residues)}")
    print(f"  locally covered residues: {len(covered_results)}")
    print(f"  failed residues: {len(failed_results)}")
    print(f"  failed r list: {[result.r for result in failed_results]}")
    print(f"  total selected rules: {len(all_selected)}")
    print(f"  max local modulus M: {max_M}")
    print(f"  largest subresidue count for one r: {max_subresidues}")
    print(f"  validation failures: {failures[:20]}{' ...' if len(failures) > 20 else ''}")
    print()

    print("most common d:")
    for d, count in d_counts.most_common(20):
        print(f"  d={d}: {count}")
    print()

    print("most common pairs:")
    for pair, count in pair_counts.most_common(20):
        print(f"  {pair}: {count}")
    print()

    if candidate_path is not None:
        print(f"candidate_cover_1_mod_24_core.md created: {candidate_path}")
        print("verdict: candidate core cover generated")
    else:
        print("candidate_cover_1_mod_24_core.md created: no")
        print("verdict: not proved yet")


if __name__ == "__main__":
    main()
