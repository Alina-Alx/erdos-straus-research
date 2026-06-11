#!/usr/bin/env python3
"""Apply prime-factor family lemmas to symbolic remaining classes.

This script takes the local family conditions discovered in
``automatic_small_factor_*`` and ``compound_factor_family_*`` and applies them
to the remaining symbolic classes:

    n == r (mod m)

It deliberately does not expand a class into a huge lifted tree.  Instead, it
checks whether a family rule fully covers, partially intersects, or misses the
class by solving small CRT intersections for the rule's positive conditions.

The output is a diagnostic symbolic cover, not a proof certificate.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
AUTOMATIC_RULES_PATH = Path("automatic_small_factor_rules.csv")
COMPOUND_RULES_PATH = Path("compound_factor_family_rules.csv")
REPORT_PATH = Path("compound_symbolic_cover_report.md")


@dataclass(frozen=True)
class Condition:
    modulus: int
    residues: frozenset[int]
    label: str


@dataclass(frozen=True)
class FamilyRule:
    d: int
    a: int
    b: int
    q: int
    source: str
    support_count: int
    conditions: tuple[Condition, ...]

    @property
    def key(self) -> str:
        return f"d={self.d},a={self.a},b={self.b}"

    @property
    def condition_signature(self) -> str:
        return " AND ".join(condition.label for condition in self.conditions)


@dataclass(frozen=True)
class RemainderClass:
    focus_r: int
    base_modulus: int
    base_residue: int
    conditions_count: int
    status: str


@dataclass(frozen=True)
class CoverEval:
    status: str
    refinement_ratio: int
    satisfying_subclasses: int
    total_subclasses: int
    reason: str


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def csv_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in ("", None) else default


def crt_intersection(m1: int, r1: int, m2: int, r2: int) -> tuple[int, int] | None:
    common = math.gcd(m1, m2)
    if (r2 - r1) % common != 0:
        return None
    reduced_m1 = m1 // common
    reduced_m2 = m2 // common
    step = ((r2 - r1) // common * pow(reduced_m1, -1, reduced_m2)) % reduced_m2
    modulus = m1 * reduced_m2
    residue = (r1 + m1 * step) % modulus
    return modulus, residue


def run_assert_tests() -> None:
    assert crt_intersection(4, 1, 6, 3) == (12, 9)
    assert crt_intersection(4, 1, 6, 2) is None
    assert crt_intersection(5, 4, 7, 6) == (35, 34)
    assert crt_intersection(12, 9, 4, 1) == (12, 9)


def local_residue_set(d: int, modulus: int) -> frozenset[int]:
    return frozenset(
        residue
        for residue in range(modulus)
        if (residue * (residue + d)) % modulus == 0
    )


def parse_int_set(text: str) -> frozenset[int]:
    return frozenset(int(part) for part in re.findall(r"\d+", text))


def parse_extra_moduli(text: str) -> list[int]:
    if not text:
        return []
    return [int(part) for part in text.split(";") if part]


def focus_remaining_path(focus_r: int) -> Path:
    return Path(f"symbolic_remainder_focus_{focus_r}_remaining.csv")


def ensure_inputs(focus_residues: list[int]) -> None:
    required = [AUTOMATIC_RULES_PATH, COMPOUND_RULES_PATH]
    required.extend(focus_remaining_path(focus_r) for focus_r in focus_residues)
    missing = [path for path in required if not path.exists()]
    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise SystemExit(f"missing required inputs:\n{formatted}")


def build_simple_rule(row: dict[str, str]) -> FamilyRule | None:
    if row.get("prime_condition_enough_on_n_1_mod_24") != "True":
        return None
    dominant_prime = csv_int(row, "dominant_prime")
    if dominant_prime <= 1:
        return None
    d = csv_int(row, "d")
    a = csv_int(row, "a")
    b = csv_int(row, "b")
    q = csv_int(row, "q")
    residues = frozenset({0, (-d) % dominant_prime})
    return FamilyRule(
        d=d,
        a=a,
        b=b,
        q=q,
        source="automatic_small_factor",
        support_count=csv_int(row, "support_count", 1),
        conditions=(
            Condition(24, frozenset({1}), "n mod 24 in {1}"),
            Condition(dominant_prime, residues, f"n mod {dominant_prime} in {{{','.join(str(x) for x in sorted(residues))}}}"),
        ),
    )


def build_compound_rule(row: dict[str, str]) -> FamilyRule | None:
    if row.get("compound_conditions_enough") != "True":
        return None
    d = csv_int(row, "d")
    a = csv_int(row, "a")
    b = csv_int(row, "b")
    q = csv_int(row, "q")
    dominant_prime = csv_int(row, "dominant_prime")
    if dominant_prime <= 1:
        return None
    prime_residues = frozenset({0, (-d) % dominant_prime})
    conditions = [
        Condition(24, frozenset({1}), "n mod 24 in {1}"),
        Condition(
            dominant_prime,
            prime_residues,
            f"n mod {dominant_prime} in {{{','.join(str(x) for x in sorted(prime_residues))}}}",
        ),
    ]
    for modulus in parse_extra_moduli(row.get("extra_moduli", "")):
        residues = local_residue_set(d, modulus)
        conditions.append(
            Condition(
                modulus,
                residues,
                f"n mod {modulus} in {{{','.join(str(x) for x in sorted(residues))}}}",
            )
        )
    return FamilyRule(
        d=d,
        a=a,
        b=b,
        q=q,
        source="compound_factor",
        support_count=csv_int(row, "support_count", 1),
        conditions=tuple(conditions),
    )


def load_family_rules(limit: int) -> list[FamilyRule]:
    rules: dict[tuple[int, int, int], FamilyRule] = {}
    for row in read_csv_rows(AUTOMATIC_RULES_PATH):
        rule = build_simple_rule(row)
        if rule is not None:
            rules[(rule.d, rule.a, rule.b)] = rule
    for row in read_csv_rows(COMPOUND_RULES_PATH):
        rule = build_compound_rule(row)
        if rule is not None:
            rules[(rule.d, rule.a, rule.b)] = rule
    return sorted(rules.values(), key=lambda rule: rule.support_count, reverse=True)[:limit]


def load_remainders(focus_r: int, sample_limit: int | None) -> list[RemainderClass]:
    remainders: list[RemainderClass] = []
    # The condition_summary field can be very large and quoted.  We only need
    # the first four simple integer fields, so parse the prefix directly.
    with focus_remaining_path(focus_r).open(encoding="utf-8") as file:
        next(file, None)
        for index, line in enumerate(file):
            if sample_limit is not None and index >= sample_limit:
                break
            first_fields = line.split(",", 4)
            if len(first_fields) < 4:
                continue
            remainders.append(
                RemainderClass(
                    focus_r=focus_r,
                    base_modulus=int(first_fields[1]),
                    base_residue=int(first_fields[2]),
                    conditions_count=int(first_fields[3]),
                    status="",
                )
            )
    return remainders


def compatible_residue_count(base_modulus: int, base_residue: int, condition: Condition) -> int:
    common = math.gcd(base_modulus, condition.modulus)
    base_mod_common = base_residue % common
    return sum(1 for residue in condition.residues if residue % common == base_mod_common)


def condition_fully_forced(base_modulus: int, base_residue: int, condition: Condition) -> bool:
    common = math.gcd(base_modulus, condition.modulus)
    compatible_total = condition.modulus // common
    return compatible_residue_count(base_modulus, base_residue, condition) == compatible_total


def condition_possible(base_modulus: int, base_residue: int, condition: Condition) -> bool:
    return compatible_residue_count(base_modulus, base_residue, condition) > 0


def conjunction_possible(
    base_modulus: int,
    base_residue: int,
    conditions: tuple[Condition, ...],
) -> bool:
    classes: set[tuple[int, int]] = {(base_modulus, base_residue % base_modulus)}
    for condition in conditions:
        next_classes: set[tuple[int, int]] = set()
        for modulus, residue in classes:
            for condition_residue in condition.residues:
                intersection = crt_intersection(
                    modulus,
                    residue,
                    condition.modulus,
                    condition_residue,
                )
                if intersection is not None:
                    next_classes.add(intersection)
        if not next_classes:
            return False
        classes = next_classes
    return True


def exact_satisfying_count(
    base_modulus: int,
    base_residue: int,
    conditions: tuple[Condition, ...],
    max_exact_ratio: int,
) -> tuple[str, int, int, str]:
    combined_modulus = base_modulus
    for condition in conditions:
        combined_modulus = lcm_many(combined_modulus, condition.modulus)
    ratio = combined_modulus // base_modulus
    if ratio > max_exact_ratio:
        possible = conjunction_possible(base_modulus, base_residue, conditions)
        status = "partial_by_crt" if possible else "none"
        reason = "exact count skipped; positive family conditions have CRT intersection" if possible else "no CRT intersection"
        return status, ratio, -1, reason

    satisfying = 0
    for candidate in range(base_residue % combined_modulus, combined_modulus, base_modulus):
        if all(candidate % condition.modulus in condition.residues for condition in conditions):
            satisfying += 1
    total = ratio
    if satisfying == 0:
        return "none", ratio, satisfying, "no subclass satisfies all family conditions"
    if satisfying == total:
        return "full", ratio, satisfying, "all subclasses satisfy family conditions"
    return "partial", ratio, satisfying, "some subclasses satisfy family conditions"


def evaluate_rule_on_class(
    rule: FamilyRule,
    remainder: RemainderClass,
    max_exact_ratio: int,
) -> CoverEval:
    # Fast full/miss checks per condition avoid exact enumeration most of the time.
    all_forced = True
    for condition in rule.conditions:
        if not condition_possible(remainder.base_modulus, remainder.base_residue, condition):
            return CoverEval("none", 1, 0, 0, f"fails {condition.label}")
        if not condition_fully_forced(remainder.base_modulus, remainder.base_residue, condition):
            all_forced = False

    combined_modulus = remainder.base_modulus
    for condition in rule.conditions:
        combined_modulus = lcm_many(combined_modulus, condition.modulus)
    ratio = combined_modulus // remainder.base_modulus
    if all_forced:
        return CoverEval("full", ratio, ratio, ratio, "all positive conditions are forced by base class")

    status, exact_ratio, satisfying, reason = exact_satisfying_count(
        remainder.base_modulus,
        remainder.base_residue,
        rule.conditions,
        max_exact_ratio,
    )
    total = exact_ratio if satisfying >= 0 else -1
    return CoverEval(status, exact_ratio, satisfying, total, reason)


def sample_solution_is_valid(rule: FamilyRule, n: int) -> bool:
    if (n + rule.d) % 4 != 0:
        return False
    product = n * (n + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def verify_full_cover_sample(rule: FamilyRule, remainder: RemainderClass) -> bool:
    for offset in range(3):
        n = remainder.base_residue + offset * remainder.base_modulus
        if n <= 1:
            n += remainder.base_modulus
        if not sample_solution_is_valid(rule, n):
            return False
    return True


def analyze_focus(
    focus_r: int,
    rules: list[FamilyRule],
    max_exact_ratio: int,
    sample_limit: int | None,
    summary_only: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    remainders = load_remainders(focus_r, sample_limit)
    class_rows: list[dict[str, object]] = []
    selected_rows: list[dict[str, object]] = []
    full = partial = unknown = missed = validation_failures = 0
    best_rule_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    for index, remainder in enumerate(remainders):
        best_rule: FamilyRule | None = None
        best_eval: CoverEval | None = None
        for rule in rules:
            evaluation = evaluate_rule_on_class(rule, remainder, max_exact_ratio)
            if evaluation.status == "none":
                continue
            best_rule = rule
            best_eval = evaluation
            if evaluation.status == "full":
                break
        if best_rule is None or best_eval is None:
            missed += 1
            status_counts["none"] += 1
            if not summary_only:
                class_rows.append(
                    {
                        "focus_r": focus_r,
                        "base_modulus": remainder.base_modulus,
                        "base_residue": remainder.base_residue,
                        "input_conditions_count": remainder.conditions_count,
                        "coverage_status": "none",
                        "rule_d": "",
                        "rule_a": "",
                        "rule_b": "",
                        "rule_source": "",
                        "refinement_ratio": "",
                        "satisfying_subclasses": "",
                        "total_subclasses": "",
                        "reason": "no family rule intersects this base class",
                        "symbolic_remainder": "unchanged",
                        "validation_passed": "",
                    }
                )
            continue

        validation_passed = ""
        if best_eval.status == "full":
            validation_passed = verify_full_cover_sample(best_rule, remainder)
            if not validation_passed:
                validation_failures += 1
        if best_eval.status == "full":
            full += 1
        elif best_eval.status in ("partial", "partial_by_crt"):
            partial += 1
        else:
            unknown += 1
        status_counts[best_eval.status] += 1
        best_rule_counts[best_rule.key] += 1
        symbolic_remainder = (
            "covered"
            if best_eval.status == "full"
            else f"base class AND NOT({best_rule.condition_signature})"
        )
        if not summary_only:
            class_rows.append(
                {
                    "focus_r": focus_r,
                    "base_modulus": remainder.base_modulus,
                    "base_residue": remainder.base_residue,
                    "input_conditions_count": remainder.conditions_count,
                    "coverage_status": best_eval.status,
                    "rule_d": best_rule.d,
                    "rule_a": best_rule.a,
                    "rule_b": best_rule.b,
                    "rule_source": best_rule.source,
                    "refinement_ratio": best_eval.refinement_ratio,
                    "satisfying_subclasses": best_eval.satisfying_subclasses,
                    "total_subclasses": best_eval.total_subclasses,
                    "reason": best_eval.reason,
                    "symbolic_remainder": symbolic_remainder,
                    "validation_passed": validation_passed,
                }
            )
            selected_rows.append(
                {
                    "focus_r": focus_r,
                    "class_index": index,
                    "d": best_rule.d,
                    "a": best_rule.a,
                    "b": best_rule.b,
                    "q": best_rule.q,
                    "source": best_rule.source,
                    "support_count": best_rule.support_count,
                    "coverage_status": best_eval.status,
                    "condition_signature": best_rule.condition_signature,
                }
            )

    summary = {
        "focus_r": focus_r,
        "total_remainders": len(remainders),
        "fully_covered": full,
        "partially_covered": partial,
        "unknown_fullness": unknown,
        "missed": missed,
        "validation_failures": validation_failures,
        "top_rules": best_rule_counts.most_common(10),
        "status_counts": status_counts.most_common(),
        "verdict": "candidate local cover" if missed == 0 and unknown == 0 and partial == 0 and validation_failures == 0 else "not proved yet",
    }
    return class_rows, selected_rows, summary


def write_report(summaries: list[dict[str, object]], rules: list[FamilyRule], sampled: bool) -> None:
    total = sum(int(summary["total_remainders"]) for summary in summaries)
    full = sum(int(summary["fully_covered"]) for summary in summaries)
    partial = sum(int(summary["partially_covered"]) for summary in summaries)
    unknown = sum(int(summary["unknown_fullness"]) for summary in summaries)
    missed = sum(int(summary["missed"]) for summary in summaries)
    failures = sum(int(summary["validation_failures"]) for summary in summaries)

    lines = [
        "# Compound Symbolic Cover Report",
        "",
        "This report applies prime-factor family lemmas to symbolic remaining",
        "classes without explicit lift-tree enumeration.",
        "",
        f"Sampled analysis only: `{'yes' if sampled else 'no'}`.",
        f"Family rules loaded: `{len(rules)}`.",
        "",
        "## Global Summary",
        "",
        f"- remainders analyzed: `{total}`",
        f"- fully covered base classes: `{full}`",
        f"- partially covered base classes: `{partial}`",
        f"- symbolic unknown fullness: `{unknown}`",
        f"- missed base classes: `{missed}`",
        f"- validation failures on full covers: `{failures}`",
        "",
        "A partial hit means the family lemma covers a symbolic subfamily and",
        "the remainder can be represented compactly as `NOT(family conditions)`.",
        "It is not proof coverage.",
        "",
        "## Focus Summaries",
        "",
    ]
    for summary in summaries:
        lines.extend(
            [
                f"### focus {summary['focus_r']}",
                "",
                f"- total: `{summary['total_remainders']}`",
                f"- full: `{summary['fully_covered']}`",
                f"- partial: `{summary['partially_covered']}`",
                f"- unknown: `{summary['unknown_fullness']}`",
                f"- missed: `{summary['missed']}`",
                f"- validation failures: `{summary['validation_failures']}`",
                f"- top rules: `{summary['top_rules']}`",
                f"- verdict: `{summary['verdict']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "The compound family lemmas now give a compact symbolic language for",
            "pieces of the remaining core. The next mathematical step is to study",
            "whether accumulated `NOT(family conditions)` remainders force another",
            "family condition, instead of adding explicit subresidues.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus-residue", type=int, choices=FOCUS_RESIDUES)
    parser.add_argument("--max-family-rules", type=int, default=250)
    parser.add_argument(
        "--max-exact-ratio",
        type=int,
        default=0,
        help="Only count satisfying subclasses exactly when lcm/base ratio is at most this value.",
    )
    parser.add_argument("--sample-limit", type=int)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    run_assert_tests()
    focus_residues = [args.focus_residue] if args.focus_residue else FOCUS_RESIDUES
    ensure_inputs(focus_residues)
    rules = load_family_rules(args.max_family_rules)
    summaries: list[dict[str, object]] = []

    for focus_r in focus_residues:
        class_rows, selected_rows, summary = analyze_focus(
            focus_r,
            rules,
            args.max_exact_ratio,
            args.sample_limit,
            args.summary_only,
        )
        summaries.append(summary)
        if not args.summary_only:
            write_csv(
                Path(f"compound_symbolic_cover_focus_{focus_r}_classes.csv"),
                [
                    "focus_r",
                    "base_modulus",
                    "base_residue",
                    "input_conditions_count",
                    "coverage_status",
                    "rule_d",
                    "rule_a",
                    "rule_b",
                    "rule_source",
                    "refinement_ratio",
                    "satisfying_subclasses",
                    "total_subclasses",
                    "reason",
                    "symbolic_remainder",
                    "validation_passed",
                ],
                class_rows,
            )
            write_csv(
                Path(f"compound_symbolic_cover_focus_{focus_r}_selected_rules.csv"),
                [
                    "focus_r",
                    "class_index",
                    "d",
                    "a",
                    "b",
                    "q",
                    "source",
                    "support_count",
                    "coverage_status",
                    "condition_signature",
                ],
                selected_rows,
            )

    write_csv(
        Path("compound_symbolic_cover_summary.csv"),
        [
            "focus_r",
            "total_remainders",
            "fully_covered",
            "partially_covered",
            "unknown_fullness",
            "missed",
            "validation_failures",
            "top_rules",
            "status_counts",
            "verdict",
        ],
        summaries,
    )
    write_report(summaries, rules, sampled=args.sample_limit is not None)

    total = sum(int(summary["total_remainders"]) for summary in summaries)
    full = sum(int(summary["fully_covered"]) for summary in summaries)
    partial = sum(int(summary["partially_covered"]) for summary in summaries)
    unknown = sum(int(summary["unknown_fullness"]) for summary in summaries)
    missed = sum(int(summary["missed"]) for summary in summaries)
    failures = sum(int(summary["validation_failures"]) for summary in summaries)
    print(f"Family rules loaded: {len(rules)}")
    print(f"Remainders analyzed: {total}")
    print(f"Fully covered base classes: {full}")
    print(f"Partially covered base classes: {partial}")
    print(f"Unknown fullness: {unknown}")
    print(f"Missed base classes: {missed}")
    print(f"Validation failures: {failures}")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
