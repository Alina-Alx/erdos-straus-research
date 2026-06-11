#!/usr/bin/env python3
"""Search for residue-class coverage of the Erdos-Straus equation.

This script is deliberately conservative.  A rule (d,a,b) is used modulo L
only when a and b divide L, so checking one residue r modulo L really fixes
the divisibility of n(n+d) by a and b for every n == r mod L.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from erdos_straus import (
    check_solution,
    first_compatible_d,
    formula_general_key,
    formula_3_mod_4,
    formula_divisible_by_3,
    formula_even,
)


BASE_METHODS = ("formula_even", "formula_divisible_by_3", "formula_3_mod_4")


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def method(self) -> str:
        return f"general_key_d_{self.d}"


@dataclass(frozen=True)
class CoverageClass:
    modulus: int
    residue: int
    method: str
    d: int | None = None
    a: int | None = None
    b: int | None = None


@dataclass(frozen=True)
class ResidueBox:
    modulus: int
    residue: int


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def sample_n_for_residue(residue: int, modulus: int) -> int:
    """Pick a concrete n > 1 from a residue class."""
    if residue > 1:
        return residue
    return residue + modulus


def base_method_for_residue(residue: int) -> str | None:
    if residue % 2 == 0:
        return "formula_even"
    if residue % 3 == 0:
        return "formula_divisible_by_3"
    if residue % 4 == 3:
        return "formula_3_mod_4"
    return None


def base_solution(method: str, n: int) -> tuple[int, int, int] | None:
    if method == "formula_even":
        return formula_even(n)
    if method == "formula_divisible_by_3":
        return formula_divisible_by_3(n)
    if method == "formula_3_mod_4":
        return formula_3_mod_4(n)
    return None


def rule_covers_residue(rule: Rule, residue: int, modulus: int) -> bool:
    """Check whether rule covers every n == residue mod modulus.

    The conditions a | modulus and b | modulus are sufficient guardrails:
    then n mod a and n mod b are fixed by n mod modulus.
    """
    if modulus % rule.a != 0 or modulus % rule.b != 0:
        return False
    if (residue + rule.d) % 4 != 0:
        return False

    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def solution_from_rule(n: int, rule: Rule) -> tuple[int, int, int]:
    x = (n + rule.d) // 4
    product = n * (n + rule.d)
    y = product // rule.a
    z = product // rule.b
    return x, y, z


def rule_modulus(rule: Rule) -> int:
    return lcm_many(4, rule.a, rule.b)


def subresidues_for_box(box: ResidueBox, new_modulus: int) -> list[int]:
    if new_modulus % box.modulus != 0:
        raise ValueError("new modulus must be a multiple of the old modulus")
    return [
        (box.residue + k * box.modulus) % new_modulus
        for k in range(new_modulus // box.modulus)
    ]


def sample_values_for_box(box: ResidueBox, count: int) -> list[int]:
    samples: list[int] = []
    k = 0
    while len(samples) < count:
        n = box.residue + k * box.modulus
        k += 1
        if n > 1:
            samples.append(n)
    return samples


def find_sample_rules(n: int, max_d: int, per_sample: int) -> list[Rule]:
    rules: list[Rule] = []
    seen: set[Rule] = set()
    for d in range(first_compatible_d(n), max_d + 1, 4):
        solution = formula_general_key(n, d)
        if solution is None:
            continue
        _, _, _, used_d, a, b = solution
        rule = Rule(used_d, a, b)
        if rule not in seen:
            rules.append(rule)
            seen.add(rule)
        if len(rules) >= per_sample:
            break
    return rules


def candidate_rules_for_box(
    box: ResidueBox,
    max_d: int,
    samples_per_box: int,
    rules_per_sample: int,
) -> list[Rule]:
    rules: list[Rule] = []
    seen: set[Rule] = set()
    for n in sample_values_for_box(box, samples_per_box):
        for rule in find_sample_rules(n, max_d, rules_per_sample):
            if rule not in seen:
                rules.append(rule)
                seen.add(rule)
    return rules


def generate_candidate_rules(modulus: int, max_d: int) -> list[Rule]:
    """Generate safe candidate rules with a+b=4d and a,b dividing modulus."""
    rules: list[Rule] = []
    for d in range(1, max_d + 1):
        pair_sum = 4 * d
        for a in range(1, pair_sum // 2 + 1):
            b = pair_sum - a
            if modulus % a == 0 and modulus % b == 0:
                rules.append(Rule(d=d, a=a, b=b))
    return rules


def build_rule_cover(
    rules: list[Rule], residues: set[int], modulus: int
) -> dict[Rule, set[int]]:
    cover: dict[Rule, set[int]] = {}
    for rule in rules:
        covered = {r for r in residues if rule_covers_residue(rule, r, modulus)}
        if covered:
            cover[rule] = covered
    return cover


def greedy_set_cover(
    rule_cover: dict[Rule, set[int]], target_residues: set[int]
) -> tuple[list[Rule], set[int]]:
    uncovered = set(target_residues)
    selected: list[Rule] = []

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

        selected.append(best_rule)
        uncovered -= best_new

    return selected, uncovered


def assign_residues(
    modulus: int,
    max_d: int,
    search_cover: bool,
) -> tuple[dict[int, dict[str, int | str | None]], list[Rule], set[int]]:
    assignments: dict[int, dict[str, int | str | None]] = {}
    all_residues = set(range(modulus))

    for residue in sorted(all_residues):
        method = base_method_for_residue(residue)
        if method is not None:
            assignments[residue] = {
                "residue": residue,
                "method": method,
                "d": None,
                "a": None,
                "b": None,
            }

    remaining = all_residues - set(assignments)
    rules = generate_candidate_rules(modulus, max_d)
    rule_cover = build_rule_cover(rules, remaining, modulus)

    if search_cover:
        selected_rules, uncovered = greedy_set_cover(rule_cover, remaining)
        for rule in selected_rules:
            for residue in sorted(rule_cover[rule]):
                if residue in remaining and residue not in uncovered and residue not in assignments:
                    assignments[residue] = {
                        "residue": residue,
                        "method": rule.method,
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                    }
        return assignments, selected_rules, uncovered

    selected_rules = []
    uncovered = set()
    for residue in sorted(remaining):
        covering_rules = [rule for rule, covered in rule_cover.items() if residue in covered]
        if not covering_rules:
            uncovered.add(residue)
            continue
        rule = min(covering_rules, key=lambda item: (item.d, item.a, item.b))
        selected_rules.append(rule)
        assignments[residue] = {
            "residue": residue,
            "method": rule.method,
            "d": rule.d,
            "a": rule.a,
            "b": rule.b,
        }

    return assignments, selected_rules, uncovered


def coverage_classes_from_assignments(
    assignments: dict[int, dict[str, int | str | None]],
    modulus: int,
) -> list[CoverageClass]:
    classes: list[CoverageClass] = []
    for residue, row in sorted(assignments.items()):
        classes.append(
            CoverageClass(
                modulus=modulus,
                residue=residue,
                method=str(row["method"]),
                d=None if row["d"] is None else int(row["d"]),
                a=None if row["a"] is None else int(row["a"]),
                b=None if row["b"] is None else int(row["b"]),
            )
        )
    return classes


def apply_rule_to_box(
    box: ResidueBox,
    rule: Rule,
    global_limit: int,
) -> tuple[list[CoverageClass], list[ResidueBox], int] | None:
    new_modulus = lcm_many(box.modulus, rule_modulus(rule))
    if new_modulus > global_limit:
        return None

    covered: list[CoverageClass] = []
    uncovered: list[ResidueBox] = []
    for subresidue in subresidues_for_box(box, new_modulus):
        if rule_covers_residue(rule, subresidue, new_modulus):
            covered.append(
                CoverageClass(
                    modulus=new_modulus,
                    residue=subresidue,
                    method=rule.method,
                    d=rule.d,
                    a=rule.a,
                    b=rule.b,
                )
            )
        else:
            uncovered.append(ResidueBox(new_modulus, subresidue))

    return covered, uncovered, new_modulus


def lift_uncovered_boxes(
    boxes: list[ResidueBox],
    max_d: int,
    global_limit: int,
    lift_rounds: int,
    samples_per_box: int,
    rules_per_sample: int,
) -> tuple[list[CoverageClass], list[ResidueBox], list[Rule]]:
    lifted_classes: list[CoverageClass] = []
    selected_rules: list[Rule] = []
    current_boxes = list(boxes)

    for _ in range(lift_rounds):
        if not current_boxes:
            break

        next_boxes: list[ResidueBox] = []
        progress = False

        for box in current_boxes:
            candidates = candidate_rules_for_box(
                box=box,
                max_d=max_d,
                samples_per_box=samples_per_box,
                rules_per_sample=rules_per_sample,
            )

            best: tuple[list[CoverageClass], list[ResidueBox], int, Rule] | None = None
            for rule in candidates:
                applied = apply_rule_to_box(box, rule, global_limit)
                if applied is None:
                    continue
                covered, uncovered, new_modulus = applied
                if not covered:
                    continue
                score = (len(covered), -new_modulus, -rule.d, -rule.a)
                if best is None:
                    best = (covered, uncovered, new_modulus, rule)
                    best_score = score
                elif score > best_score:
                    best = (covered, uncovered, new_modulus, rule)
                    best_score = score

            if best is None:
                next_boxes.append(box)
                continue

            covered, uncovered, _, rule = best
            lifted_classes.extend(covered)
            selected_rules.append(rule)
            next_boxes.extend(uncovered)
            progress = True

        current_boxes = sorted(set(next_boxes), key=lambda item: (item.modulus, item.residue))
        if not progress:
            break

    return lifted_classes, current_boxes, selected_rules


def validate_assignments(
    assignments: dict[int, dict[str, int | str | None]], modulus: int
) -> list[str]:
    failures: list[str] = []

    for residue, assignment in sorted(assignments.items()):
        n = sample_n_for_residue(residue, modulus)
        method = str(assignment["method"])

        if method in BASE_METHODS:
            solution = base_solution(method, n)
            if solution is None or not check_solution(n, *solution):
                failures.append(f"residue {residue}: base method failed sample n={n}")
            continue

        d = int(assignment["d"])
        a = int(assignment["a"])
        b = int(assignment["b"])
        if (n + d) % 4 != 0:
            failures.append(f"residue {residue}: n+d not divisible by 4 for sample n={n}")
            continue

        product = n * (n + d)
        if product % a != 0 or product % b != 0:
            failures.append(f"residue {residue}: divisibility failed for sample n={n}")
            continue

        solution = solution_from_rule(n, Rule(d=d, a=a, b=b))
        if not check_solution(n, *solution):
            failures.append(f"residue {residue}: check_solution failed for sample n={n}")

    return failures


def validate_coverage_classes(classes: list[CoverageClass]) -> list[str]:
    failures: list[str] = []
    for coverage in classes:
        n = sample_n_for_residue(coverage.residue, coverage.modulus)
        if coverage.method in BASE_METHODS:
            solution = base_solution(coverage.method, n)
            if solution is None or not check_solution(n, *solution):
                failures.append(
                    f"mod {coverage.modulus} residue {coverage.residue}: "
                    f"base method failed sample n={n}"
                )
            continue

        if coverage.d is None or coverage.a is None or coverage.b is None:
            failures.append(
                f"mod {coverage.modulus} residue {coverage.residue}: missing rule data"
            )
            continue
        if coverage.modulus % 4 != 0 or coverage.modulus % coverage.a != 0 or coverage.modulus % coverage.b != 0:
            failures.append(
                f"mod {coverage.modulus} residue {coverage.residue}: modulus does not stabilize rule"
            )
            continue
        rule = Rule(coverage.d, coverage.a, coverage.b)
        if not rule_covers_residue(rule, coverage.residue, coverage.modulus):
            failures.append(
                f"mod {coverage.modulus} residue {coverage.residue}: rule conditions fail"
            )
            continue
        solution = solution_from_rule(n, rule)
        if not check_solution(n, *solution):
            failures.append(
                f"mod {coverage.modulus} residue {coverage.residue}: check_solution failed"
            )
    return failures


def global_modulus_for_classes(classes: list[CoverageClass], global_limit: int) -> tuple[int, bool]:
    global_modulus = 1
    for coverage in classes:
        global_modulus = lcm_many(global_modulus, coverage.modulus)
        if global_modulus > global_limit:
            return global_modulus, False
    return global_modulus, True


def verify_global_coverage(
    classes: list[CoverageClass],
    global_limit: int,
) -> tuple[int, list[int] | None, str | None]:
    global_modulus, ok = global_modulus_for_classes(classes, global_limit)
    if not ok:
        return global_modulus, None, "GLOBAL modulus exceeds limit"

    covered = [False] * global_modulus
    for coverage in classes:
        for residue in range(coverage.residue, global_modulus, coverage.modulus):
            covered[residue] = True

    uncovered = [residue for residue, is_covered in enumerate(covered) if not is_covered]
    return global_modulus, uncovered, None


def write_coverage_csv(
    assignments: dict[int, dict[str, int | str | None]],
    modulus: int,
    uncovered: set[int],
) -> Path:
    path = Path(f"residue_coverage_mod_{modulus}.csv")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["residue", "method", "d", "a", "b"])
        writer.writeheader()
        for residue in range(modulus):
            if residue in assignments:
                writer.writerow(assignments[residue])
            else:
                writer.writerow(
                    {"residue": residue, "method": "uncovered", "d": "", "a": "", "b": ""}
                )
    return path


def write_mixed_coverage_csv(classes: list[CoverageClass], base_modulus: int) -> Path:
    path = Path(f"lifted_coverage_from_mod_{base_modulus}.csv")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["modulus", "residue", "method", "d", "a", "b"],
        )
        writer.writeheader()
        for coverage in sorted(classes, key=lambda item: (item.modulus, item.residue, item.method)):
            writer.writerow(
                {
                    "modulus": coverage.modulus,
                    "residue": coverage.residue,
                    "method": coverage.method,
                    "d": "" if coverage.d is None else coverage.d,
                    "a": "" if coverage.a is None else coverage.a,
                    "b": "" if coverage.b is None else coverage.b,
                }
            )
    return path


def write_mixed_certificate(
    classes: list[CoverageClass],
    base_modulus: int,
    global_modulus: int,
    max_d: int,
) -> Path:
    path = Path("proof_certificate.md")
    lines = [
        "# Candidate Proof Certificate",
        "",
        "This is a computer-found proof certificate. It must be independently checked mathematically.",
        "",
        "## Statement",
        "",
        "For every integer `n > 1`, the Erdos-Straus conjecture asks for positive integers `x,y,z` such that:",
        "",
        "```text",
        "4/n = 1/x + 1/y + 1/z",
        "```",
        "",
        "## Base Formulas",
        "",
        "- If `n` is even: `4/n = 1/(n/2) + 1/n + 1/n`.",
        "- If `3 | n`: `4/n = 1/(n/3) + 1/(2n) + 1/(2n)`.",
        "- If `n == 3 mod 4`: `4/n = 1/((n+1)/4) + 1/(n(n+1)/2) + 1/(n(n+1)/2)`.",
        "",
        "## General Key Lemma",
        "",
        "Suppose there are positive integers `d,a,b` such that:",
        "",
        "- `n+d` is divisible by `4`;",
        "- `a+b = 4d`;",
        "- `a` divides `n(n+d)`;",
        "- `b` divides `n(n+d)`.",
        "",
        "Let `x=(n+d)/4`, `y=n(n+d)/a`, and `z=n(n+d)/b`.",
        "",
        "Then:",
        "",
        "```text",
        "1/x + 1/y + 1/z",
        "= 4/(n+d) + a/[n(n+d)] + b/[n(n+d)]",
        "= 4/(n+d) + 4d/[n(n+d)]",
        "= 4/n",
        "```",
        "",
        "## Mixed Residue-Class Coverage",
        "",
        f"Base modulus: `{base_modulus}`",
        f"GLOBAL verification modulus: `{global_modulus}`",
        f"Max d searched: `{max_d}`",
        "",
        "The classes below may use different moduli. The verifier lifts all of them to the GLOBAL modulus and checks that every residue class is covered before writing this file.",
        "",
        "| modulus | residue | method | d | a | b |",
        "| ------- | ------- | ------ | - | - | - |",
    ]

    for coverage in sorted(classes, key=lambda item: (item.modulus, item.residue, item.method)):
        lines.append(
            f"| {coverage.modulus} | {coverage.residue} | {coverage.method} | "
            f"{coverage.d or ''} | {coverage.a or ''} | {coverage.b or ''} |"
        )

    lines += [
        "",
        "## Honest Conclusion",
        "",
        "All residue classes modulo the GLOBAL modulus are covered by the formulas in this certificate.",
        "",
        "This is a candidate proof certificate, not a peer-reviewed theorem. It should be independently checked mathematically.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_certificate(
    assignments: dict[int, dict[str, int | str | None]],
    modulus: int,
    max_d: int,
) -> Path:
    path = Path("proof_certificate.md")
    lines = [
        "# Candidate Proof Certificate",
        "",
        "This is a computer-found proof certificate. It must be independently checked mathematically.",
        "",
        "## Statement",
        "",
        "For every integer `n > 1`, the Erdos-Straus conjecture asks for positive integers `x,y,z` such that:",
        "",
        "```text",
        "4/n = 1/x + 1/y + 1/z",
        "```",
        "",
        "## Base Formulas",
        "",
        "- If `n` is even: `4/n = 1/(n/2) + 1/n + 1/n`.",
        "- If `3 | n`: `4/n = 1/(n/3) + 1/(2n) + 1/(2n)`.",
        "- If `n == 3 mod 4`: `4/n = 1/((n+1)/4) + 1/(n(n+1)/2) + 1/(n(n+1)/2)`.",
        "",
        "## General Key Lemma",
        "",
        "Suppose there are positive integers `d,a,b` such that:",
        "",
        "- `n+d` is divisible by `4`;",
        "- `a+b = 4d`;",
        "- `a` divides `n(n+d)`;",
        "- `b` divides `n(n+d)`.",
        "",
        "Let:",
        "",
        "```text",
        "x = (n+d)/4",
        "y = n(n+d)/a",
        "z = n(n+d)/b",
        "```",
        "",
        "Then:",
        "",
        "```text",
        "1/x = 4/(n+d)",
        "1/y + 1/z = a/[n(n+d)] + b/[n(n+d)]",
        "            = (a+b)/[n(n+d)]",
        "            = 4d/[n(n+d)]",
        "```",
        "",
        "Therefore:",
        "",
        "```text",
        "1/x + 1/y + 1/z",
        "= 4/(n+d) + 4d/[n(n+d)]",
        "= 4n/[n(n+d)] + 4d/[n(n+d)]",
        "= 4(n+d)/[n(n+d)]",
        "= 4/n",
        "```",
        "",
        "## Residue-Class Coverage",
        "",
        f"Modulus: `{modulus}`",
        f"Max d searched: `{max_d}`",
        "",
        "The automated search only uses general-key rules where `a | L` and `b | L`, with `L` equal to the modulus. This guardrail makes the residue-class divisibility check stable for every `n == r mod L`.",
        "",
        "| residue r | method | d | a | b |",
        "| --------- | ------ | - | - | - |",
    ]

    for residue in range(modulus):
        row = assignments[residue]
        lines.append(
            f"| {residue} | {row['method']} | {row['d'] or ''} | {row['a'] or ''} | {row['b'] or ''} |"
        )

    lines += [
        "",
        "## Honest Conclusion",
        "",
        "All residue classes modulo this `L` are covered by the formulas in this certificate.",
        "",
        "This is a candidate proof certificate, not a peer-reviewed theorem. It should be independently checked, especially the residue-class coverage table and the guardrail assumptions.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def print_summary(
    modulus: int,
    max_d: int,
    assignments: dict[int, dict[str, int | str | None]],
    selected_rules: list[Rule],
    uncovered: set[int],
    validation_failures: list[str],
    coverage_csv: Path,
    certificate: Path | None,
) -> None:
    covered = len(assignments)
    base_count = sum(1 for row in assignments.values() if row["method"] in BASE_METHODS)
    general_count = covered - base_count
    method_counts = Counter(str(row["method"]) for row in assignments.values())
    selected_set = set(selected_rules)
    assigned_rule_counts: Counter[Rule] = Counter()
    for row in assignments.values():
        if row["method"] in BASE_METHODS:
            continue
        rule = Rule(d=int(row["d"]), a=int(row["a"]), b=int(row["b"]))
        if rule in selected_set:
            assigned_rule_counts[rule] += 1

    print(f"modulus: {modulus}")
    print(f"max_d_for_proof: {max_d}")
    print(f"covered residue classes: {covered} / {modulus}")
    print(f"base-covered classes: {base_count}")
    print(f"general-key-covered classes: {general_count}")
    print(f"uncovered residue classes: {len(uncovered)}")
    print(f"coverage CSV: {coverage_csv}")
    print()

    print("method distribution:")
    for method, count in method_counts.most_common():
        print(f"  {method}: {count}")
    print()

    print("selected rules:")
    if not selected_rules:
        print("  none")
    for rule in selected_rules:
        print(
            f"  d={rule.d}, a={rule.a}, b={rule.b}: "
            f"assigned {assigned_rule_counts[rule]} class(es)"
        )
    print()

    print("uncovered residues:")
    print(sorted(uncovered) if uncovered else [])
    print()

    print("sample validation failures:")
    print(validation_failures if validation_failures else [])
    print()

    if certificate is not None:
        print(f"candidate proof certificate generated: {certificate}")
        print("verdict: candidate proof certificate generated")
    else:
        print("proof certificate: not generated")
        print("verdict: not proved yet")


def print_lifted_summary(
    modulus: int,
    max_d: int,
    before_uncovered: set[int],
    initial_classes: list[CoverageClass],
    lifted_classes: list[CoverageClass],
    remaining_boxes: list[ResidueBox],
    selected_rules: list[Rule],
    class_failures: list[str],
    global_modulus: int,
    global_uncovered: list[int] | None,
    global_warning: str | None,
    coverage_csv: Path,
    certificate: Path | None,
) -> None:
    all_classes = initial_classes + lifted_classes
    covered_after_lift = len(lifted_classes)
    method_counts = Counter(coverage.method for coverage in all_classes)
    rule_counts = Counter(selected_rules)

    print(f"modulus: {modulus}")
    print(f"max_d_for_proof: {max_d}")
    print(f"uncovered residues before lift: {len(before_uncovered)}")
    print(f"before-lift uncovered residues: {sorted(before_uncovered)}")
    print(f"lifted classes added: {covered_after_lift}")
    print(f"remaining uncovered classes after lift: {len(remaining_boxes)}")
    print(f"mixed coverage CSV: {coverage_csv}")
    print(f"GLOBAL modulus: {global_modulus}")
    if global_warning:
        print(f"GLOBAL verification warning: {global_warning}")
    print()

    print("method distribution across mixed classes:")
    for method, count in method_counts.most_common():
        print(f"  {method}: {count}")
    print()

    print("selected lift rules:")
    if not selected_rules:
        print("  none")
    for rule, count in rule_counts.most_common():
        print(f"  d={rule.d}, a={rule.a}, b={rule.b}: selected {count} time(s)")
    print()

    print("classes still uncovered:")
    if remaining_boxes:
        for box in remaining_boxes[:200]:
            print(f"  mod {box.modulus}, residue {box.residue}")
        if len(remaining_boxes) > 200:
            print(f"  ... {len(remaining_boxes) - 200} more")
    else:
        print("  none")
    print()

    print("GLOBAL uncovered residues:")
    if global_uncovered is None:
        print("  not checked")
    elif global_uncovered:
        print(f"  {global_uncovered[:200]}")
        if len(global_uncovered) > 200:
            print(f"  ... {len(global_uncovered) - 200} more")
    else:
        print("  none")
    print()

    print("sample validation failures:")
    print(class_failures if class_failures else [])
    print()

    if certificate is not None:
        print(f"candidate proof certificate generated: {certificate}")
        print("verdict: candidate proof certificate generated")
    else:
        print("proof certificate: not generated")
        print("verdict: not proved yet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search residue-class formula coverage for Erdos-Straus."
    )
    parser.add_argument("--modulus", type=int, default=840)
    parser.add_argument("--max-d", type=int, default=500)
    parser.add_argument("--search-cover", action="store_true")
    parser.add_argument("--lift-uncovered", action="store_true")
    parser.add_argument(
        "--global-limit",
        type=int,
        default=10_000_000,
        help="maximum GLOBAL modulus allowed for certificate verification",
    )
    parser.add_argument("--lift-rounds", type=int, default=1)
    parser.add_argument("--samples-per-box", type=int, default=4)
    parser.add_argument("--rules-per-sample", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.modulus < 1:
        raise SystemExit("--modulus must be positive")
    if args.max_d < 1:
        raise SystemExit("--max-d must be positive")
    if args.global_limit < 1:
        raise SystemExit("--global-limit must be positive")

    assignments, selected_rules, uncovered = assign_residues(
        modulus=args.modulus,
        max_d=args.max_d,
        search_cover=args.search_cover,
    )

    if args.lift_uncovered:
        initial_classes = coverage_classes_from_assignments(assignments, args.modulus)
        initial_boxes = [ResidueBox(args.modulus, residue) for residue in sorted(uncovered)]
        lifted_classes, remaining_boxes, lift_rules = lift_uncovered_boxes(
            boxes=initial_boxes,
            max_d=args.max_d,
            global_limit=args.global_limit,
            lift_rounds=args.lift_rounds,
            samples_per_box=args.samples_per_box,
            rules_per_sample=args.rules_per_sample,
        )
        all_classes = initial_classes + lifted_classes
        class_failures = validate_coverage_classes(all_classes)
        coverage_csv = write_mixed_coverage_csv(all_classes, args.modulus)
        global_modulus, global_uncovered, global_warning = verify_global_coverage(
            all_classes,
            args.global_limit,
        )

        certificate = None
        if (
            not remaining_boxes
            and not class_failures
            and global_warning is None
            and global_uncovered == []
        ):
            certificate = write_mixed_certificate(
                all_classes,
                args.modulus,
                global_modulus,
                args.max_d,
            )

        print_lifted_summary(
            modulus=args.modulus,
            max_d=args.max_d,
            before_uncovered=uncovered,
            initial_classes=initial_classes,
            lifted_classes=lifted_classes,
            remaining_boxes=remaining_boxes,
            selected_rules=lift_rules,
            class_failures=class_failures,
            global_modulus=global_modulus,
            global_uncovered=global_uncovered,
            global_warning=global_warning,
            coverage_csv=coverage_csv,
            certificate=certificate,
        )
        return

    validation_failures = validate_assignments(assignments, args.modulus)
    coverage_csv = write_coverage_csv(assignments, args.modulus, uncovered)

    certificate = None
    if not uncovered and not validation_failures:
        certificate = write_certificate(assignments, args.modulus, args.max_d)

    print_summary(
        modulus=args.modulus,
        max_d=args.max_d,
        assignments=assignments,
        selected_rules=selected_rules,
        uncovered=uncovered,
        validation_failures=validation_failures,
        coverage_csv=coverage_csv,
        certificate=certificate,
    )


if __name__ == "__main__":
    main()
