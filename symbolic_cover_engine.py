#!/usr/bin/env python3
"""Symbolic cover engine for hard Erdos-Straus focus classes.

The earlier recursive cover search lifted unresolved classes by explicitly
enumerating subclasses. This diagnostic keeps a class as a congruence

    n == residue (mod modulus)

and intersects it with a fixed general-key rule through the small residue set
of that rule modulo q = lcm(4, a, b). It is a research tool, not a proof
certificate generator.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from erdos_straus import check_solution


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
RULE_RESIDUE_PATH = Path("symbolic_rule_residue_sets.csv")
RULE_SUMMARY_PATH = Path("symbolic_rule_summary.csv")
MASTER_KEYS_PATH = Path("symbolic_master_keys.csv")
REPORT_PATH = Path("symbolic_cover_report.md")


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def csv_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    return int(value) if value not in ("", None) else default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def focus_unresolved_path(focus_r: int) -> Path:
    return Path(f"recursive_focus_{focus_r}_unresolved.csv")


def required_paths() -> list[Path]:
    paths = [RULE_RESIDUE_PATH, RULE_SUMMARY_PATH, MASTER_KEYS_PATH]
    paths.extend(focus_unresolved_path(focus_r) for focus_r in FOCUS_RESIDUES)
    return paths


def ensure_inputs() -> None:
    missing = [path for path in required_paths() if not path.exists()]
    if not missing:
        return
    formatted = "\n".join(f"  - {path}" for path in missing)
    raise SystemExit(f"missing required symbolic cover inputs:\n{formatted}")


@dataclass(frozen=True)
class ClassConstraint:
    """Symbolic unresolved leaf: n is fixed modulo ``modulus``."""

    modulus: int
    residue: int
    focus_r: int
    depth: int
    source: str
    class_id: str

    @property
    def normalized_residue(self) -> int:
        return self.residue % self.modulus


@dataclass(frozen=True)
class RuleKey:
    d: int
    a: int
    b: int

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)


@dataclass(frozen=True)
class Rule:
    """General-key rule with its working residue set modulo q."""

    d: int
    a: int
    b: int
    covered_residues: frozenset[int]
    rank_score: int = 0
    sources: tuple[str, ...] = field(default_factory=tuple)

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)

    @property
    def covered_residue_count(self) -> int:
        return len(self.covered_residues)

    @property
    def pair_sum_ok(self) -> bool:
        return self.a + self.b == 4 * self.d

    @property
    def key(self) -> RuleKey:
        return RuleKey(self.d, self.a, self.b)

    def solution_for(self, n: int) -> tuple[int, int, int] | None:
        """Build x, y, z from this fixed general-key rule for one n."""
        if not self.pair_sum_ok or (n + self.d) % 4 != 0:
            return None
        product = n * (n + self.d)
        if product % self.a != 0 or product % self.b != 0:
            return None
        x = (n + self.d) // 4
        y = product // self.a
        z = product // self.b
        return (x, y, z)


@dataclass(frozen=True)
class CoverageEvaluation:
    """How one rule intersects one symbolic class."""

    status: str
    intersection_count: int
    refinement_ratio: int
    fully_checked: bool
    reason: str


@dataclass
class RuleCoverage:
    rule: Rule
    full_indices: set[int] = field(default_factory=set)
    partial_indices: set[int] = field(default_factory=set)
    unknown_indices: set[int] = field(default_factory=set)

    @property
    def touched_indices(self) -> set[int]:
        return self.full_indices | self.partial_indices | self.unknown_indices


def crt_intersection(m1: int, r1: int, m2: int, r2: int) -> tuple[int, int] | None:
    """Return the CRT intersection of two congruence classes, if it exists."""
    if m1 <= 0 or m2 <= 0:
        raise ValueError("CRT moduli must be positive")
    r1 %= m1
    r2 %= m2
    common = math.gcd(m1, m2)
    if (r2 - r1) % common != 0:
        return None

    reduced_m1 = m1 // common
    reduced_m2 = m2 // common
    step = ((r2 - r1) // common * pow(reduced_m1, -1, reduced_m2)) % reduced_m2
    new_modulus = m1 * reduced_m2
    new_residue = (r1 + m1 * step) % new_modulus
    return (new_modulus, new_residue)


def run_assert_tests() -> None:
    assert crt_intersection(4, 1, 6, 3) == (12, 9)
    assert crt_intersection(4, 1, 6, 2) is None
    assert crt_intersection(5, 4, 7, 6) == (35, 34)
    assert crt_intersection(12, 9, 4, 1) == (12, 9)


def load_classes(focus_r: int) -> list[ClassConstraint]:
    rows = read_csv_rows(focus_unresolved_path(focus_r))
    classes: list[ClassConstraint] = []
    for row in rows:
        classes.append(
            ClassConstraint(
                modulus=int(row["modulus"]),
                residue=int(row["residue"]),
                focus_r=focus_r,
                depth=int(row["depth"]),
                source=row.get("reason", "unresolved_focus_leaf"),
                class_id=row.get("class_id", ""),
            )
        )
    return classes


def residue_sets_from_csv() -> dict[RuleKey, frozenset[int]]:
    residues: defaultdict[RuleKey, set[int]] = defaultdict(set)
    for row in read_csv_rows(RULE_RESIDUE_PATH):
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        residues[key].add(int(row["residue_t"]) % key.q)
    return {key: frozenset(values) for key, values in residues.items()}


def rule_covers_residue(key: RuleKey, residue: int) -> bool:
    if not (key.a + key.b == 4 * key.d):
        return False
    if (residue + key.d) % 4 != 0:
        return False
    product = residue * (residue + key.d)
    return product % key.a == 0 and product % key.b == 0


def build_residue_set(key: RuleKey, max_rule_q: int) -> frozenset[int] | None:
    if key.q > max_rule_q:
        return None
    residues = {
        residue
        for residue in range(key.q)
        if rule_covers_residue(key, residue)
    }
    return frozenset(residues)


def candidate_rule_scores(
    focus_r: int,
    summary_rule_limit: int,
    master_rule_limit: int,
) -> tuple[Counter[RuleKey], defaultdict[RuleKey, set[str]]]:
    scores: Counter[RuleKey] = Counter()
    sources: defaultdict[RuleKey, set[str]] = defaultdict(set)

    summary_rows = sorted(
        read_csv_rows(RULE_SUMMARY_PATH),
        key=lambda row: csv_int(row, "diagnostic_leaf_count"),
        reverse=True,
    )
    for row in summary_rows[:summary_rule_limit]:
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        scores[key] += csv_int(row, "diagnostic_leaf_count", 1)
        sources[key].add("rule_summary")

    master_rows = [
        row
        for row in read_csv_rows(MASTER_KEYS_PATH)
        if csv_int(row, "focus_r") == focus_r
    ]
    master_rows.sort(key=lambda row: csv_int(row, "count"), reverse=True)
    for row in master_rows[:master_rule_limit]:
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        scores[key] += csv_int(row, "count", 1)
        sources[key].add(f"master_keys_focus_{focus_r}")

    return scores, sources


def load_candidate_rules(
    focus_r: int,
    rule_limit: int,
    summary_rule_limit: int,
    master_rule_limit: int,
    max_rule_q: int,
) -> tuple[list[Rule], list[RuleKey]]:
    known_residues = residue_sets_from_csv()
    scores, sources = candidate_rule_scores(focus_r, summary_rule_limit, master_rule_limit)
    skipped: list[RuleKey] = []
    rules: list[Rule] = []

    for key, score in scores.most_common():
        residues = known_residues.get(key)
        if residues is None:
            residues = build_residue_set(key, max_rule_q)
        if residues is None or not residues:
            skipped.append(key)
            continue
        rules.append(
            Rule(
                d=key.d,
                a=key.a,
                b=key.b,
                covered_residues=residues,
                rank_score=score,
                sources=tuple(sorted(sources[key])),
            )
        )
        if len(rules) >= rule_limit:
            break
    return rules, skipped


def compatible_rule_residues(class_constraint: ClassConstraint, rule: Rule) -> list[int]:
    compatible: list[int] = []
    for residue in rule.covered_residues:
        if crt_intersection(
            class_constraint.modulus,
            class_constraint.normalized_residue,
            rule.q,
            residue,
        ) is not None:
            compatible.append(residue)
    return compatible


def fully_covered_by_residue_set(
    class_constraint: ClassConstraint,
    rule: Rule,
    refinement_ratio: int,
) -> bool:
    common = math.gcd(class_constraint.modulus, rule.q)
    start = class_constraint.normalized_residue % common
    needed_residues = set(range(start, rule.q, common))
    if len(needed_residues) != refinement_ratio:
        raise AssertionError("refinement ratio and compatible residue count disagree")
    return needed_residues.issubset(rule.covered_residues)


def evaluate_coverage(
    class_constraint: ClassConstraint,
    rule: Rule,
    max_refinement_ratio: int,
) -> CoverageEvaluation:
    common = math.gcd(class_constraint.modulus, rule.q)
    refinement_ratio = rule.q // common
    intersections = compatible_rule_residues(class_constraint, rule)
    if not intersections:
        return CoverageEvaluation(
            status="covers_nothing",
            intersection_count=0,
            refinement_ratio=refinement_ratio,
            fully_checked=refinement_ratio <= max_refinement_ratio,
            reason="no_crt_intersection",
        )
    if refinement_ratio > max_refinement_ratio:
        return CoverageEvaluation(
            status="symbolic_partial_unknown_fullness",
            intersection_count=len(intersections),
            refinement_ratio=refinement_ratio,
            fully_checked=False,
            reason="refinement_ratio_exceeds_limit",
        )
    if fully_covered_by_residue_set(class_constraint, rule, refinement_ratio):
        return CoverageEvaluation(
            status="fully_covers",
            intersection_count=len(intersections),
            refinement_ratio=refinement_ratio,
            fully_checked=True,
            reason="every_refined_subclass_hits_rule_residue_set",
        )
    return CoverageEvaluation(
        status="partially_covers",
        intersection_count=len(intersections),
        refinement_ratio=refinement_ratio,
        fully_checked=True,
        reason="some_refined_subclasses_hit_rule_residue_set",
    )


def matrix_path(focus_r: int) -> Path:
    return Path(f"symbolic_cover_focus_{focus_r}_class_rule_matrix.csv")


def build_rule_coverages(
    focus_r: int,
    classes: list[ClassConstraint],
    rules: list[Rule],
    max_refinement_ratio: int,
) -> list[RuleCoverage]:
    fieldnames = [
        "focus_r",
        "class_index",
        "class_id",
        "depth",
        "modulus",
        "residue",
        "source",
        "d",
        "a",
        "b",
        "q",
        "covered_residue_count",
        "coverage_status",
        "intersection_count",
        "refinement_ratio",
        "fully_checked",
        "reason",
    ]
    coverages: list[RuleCoverage] = []
    with matrix_path(focus_r).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for rule in rules:
            rule_coverage = RuleCoverage(rule=rule)
            for index, class_constraint in enumerate(classes):
                evaluation = evaluate_coverage(class_constraint, rule, max_refinement_ratio)
                if evaluation.status == "covers_nothing":
                    continue
                if evaluation.status == "fully_covers":
                    rule_coverage.full_indices.add(index)
                elif evaluation.status == "partially_covers":
                    rule_coverage.partial_indices.add(index)
                else:
                    rule_coverage.unknown_indices.add(index)
                writer.writerow(
                    {
                        "focus_r": focus_r,
                        "class_index": index,
                        "class_id": class_constraint.class_id,
                        "depth": class_constraint.depth,
                        "modulus": class_constraint.modulus,
                        "residue": class_constraint.normalized_residue,
                        "source": class_constraint.source,
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                        "q": rule.q,
                        "covered_residue_count": rule.covered_residue_count,
                        "coverage_status": evaluation.status,
                        "intersection_count": evaluation.intersection_count,
                        "refinement_ratio": evaluation.refinement_ratio,
                        "fully_checked": evaluation.fully_checked,
                        "reason": evaluation.reason,
                    }
                )
            coverages.append(rule_coverage)
    return coverages


def greedy_select_coverages(
    coverages: list[RuleCoverage],
    class_count: int,
    max_selected_rules: int,
) -> list[RuleCoverage]:
    selected: list[RuleCoverage] = []
    used_rules: set[RuleKey] = set()
    closed: set[int] = set()
    all_indices = set(range(class_count))

    for _ in range(max_selected_rules):
        best_coverage: RuleCoverage | None = None
        best_score: tuple[int, int, int, int] | None = None
        active = all_indices - closed
        for coverage in coverages:
            if coverage.rule.key in used_rules:
                continue
            new_full = len(coverage.full_indices & active)
            new_partial = len((coverage.partial_indices | coverage.unknown_indices) & active)
            if new_full == 0 and new_partial == 0:
                continue
            score = (
                new_full,
                new_partial,
                coverage.rule.rank_score,
                coverage.rule.covered_residue_count,
            )
            if best_score is None or score > best_score:
                best_score = score
                best_coverage = coverage
        if best_coverage is None:
            break
        selected.append(best_coverage)
        used_rules.add(best_coverage.rule.key)
        closed.update(best_coverage.full_indices)
        if len(closed) == class_count:
            break
    return selected


def sample_values(class_constraint: ClassConstraint) -> list[int]:
    start = class_constraint.normalized_residue
    if start <= 1:
        start += class_constraint.modulus
    return [start + offset * class_constraint.modulus for offset in range(3)]


def verify_full_class(class_constraint: ClassConstraint, rule: Rule) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for n in sample_values(class_constraint):
        solution = rule.solution_for(n)
        if solution is not None and check_solution(n, *solution):
            continue
        failures.append(
            {
                "focus_r": class_constraint.focus_r,
                "class_id": class_constraint.class_id,
                "modulus": class_constraint.modulus,
                "residue": class_constraint.normalized_residue,
                "sample_n": n,
                "d": rule.d,
                "a": rule.a,
                "b": rule.b,
            }
        )
    return failures


def assign_selected_rules(
    selected: list[RuleCoverage],
    class_count: int,
) -> tuple[dict[int, Rule], defaultdict[int, list[Rule]], defaultdict[int, list[Rule]]]:
    full_owner: dict[int, Rule] = {}
    partial_rules: defaultdict[int, list[Rule]] = defaultdict(list)
    unknown_rules: defaultdict[int, list[Rule]] = defaultdict(list)
    all_indices = set(range(class_count))

    for coverage in selected:
        open_indices = all_indices - set(full_owner)
        for index in coverage.full_indices & open_indices:
            full_owner[index] = coverage.rule
        open_indices = all_indices - set(full_owner)
        for index in coverage.partial_indices & open_indices:
            partial_rules[index].append(coverage.rule)
        for index in coverage.unknown_indices & open_indices:
            unknown_rules[index].append(coverage.rule)
    return full_owner, partial_rules, unknown_rules


def condition_text(rule: Rule, unknown: bool = False) -> str:
    mode = "candidate-not" if unknown else "not"
    return (
        f"{mode}(n mod {rule.q} in S[d={rule.d},a={rule.a},"
        f"b={rule.b},size={rule.covered_residue_count}])"
    )


def write_selected_rules(
    focus_r: int,
    selected: list[RuleCoverage],
) -> None:
    rows: list[dict[str, object]] = []
    for selected_order, coverage in enumerate(selected, start=1):
        rows.append(
            {
                "focus_r": focus_r,
                "d": coverage.rule.d,
                "a": coverage.rule.a,
                "b": coverage.rule.b,
                "q": coverage.rule.q,
                "covered_residue_count": coverage.rule.covered_residue_count,
                "selected_order": selected_order,
                "classes_fully_covered": len(coverage.full_indices),
                "classes_partially_covered": len(
                    coverage.partial_indices | coverage.unknown_indices
                ),
            }
        )
    write_csv(
        Path(f"symbolic_cover_focus_{focus_r}_selected_rules.csv"),
        [
            "focus_r",
            "d",
            "a",
            "b",
            "q",
            "covered_residue_count",
            "selected_order",
            "classes_fully_covered",
            "classes_partially_covered",
        ],
        rows,
    )


def write_remainders(
    focus_r: int,
    classes: list[ClassConstraint],
    full_indices: set[int],
    partial_rules: defaultdict[int, list[Rule]],
    unknown_rules: defaultdict[int, list[Rule]],
) -> int:
    rows: list[dict[str, object]] = []
    for index, class_constraint in enumerate(classes):
        if index in full_indices:
            continue
        partial_conditions = [condition_text(rule) for rule in partial_rules[index]]
        unknown_conditions = [condition_text(rule, unknown=True) for rule in unknown_rules[index]]
        conditions = partial_conditions + unknown_conditions
        if unknown_conditions:
            status = "symbolic_partial_unknown_fullness"
        elif partial_conditions:
            status = "symbolic_remainder"
        else:
            status = "uncovered"
        rows.append(
            {
                "focus_r": focus_r,
                "base_modulus": class_constraint.modulus,
                "base_residue": class_constraint.normalized_residue,
                "conditions_count": len(conditions),
                "condition_summary": " AND ".join(conditions),
                "status": status,
            }
        )
    write_csv(
        Path(f"symbolic_cover_focus_{focus_r}_remainders.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "conditions_count",
            "condition_summary",
            "status",
        ],
        rows,
    )
    return len(rows)


def write_candidate_focus_file(
    focus_r: int,
    classes: list[ClassConstraint],
    selected: list[RuleCoverage],
) -> None:
    lines = [
        f"# Candidate Symbolic Focus Cover for {focus_r}",
        "",
        "This is a candidate symbolic cover for one focus residue class,",
        "not a proof of the full Erdos-Straus conjecture.",
        "",
        f"Fully covered symbolic leaf classes checked: `{len(classes)}`.",
        "Each fully covered class used finite refinement checks and sample",
        "verification through `check_solution`.",
        "",
        "## Selected Rules",
        "",
        "| order | d | a | b | q | covered residues |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for order, coverage in enumerate(selected, start=1):
        rule = coverage.rule
        lines.append(
            f"| {order} | {rule.d} | {rule.a} | {rule.b} | {rule.q} | "
            f"{rule.covered_residue_count} |"
        )
    lines.extend(
        [
            "",
            "Needs independent mathematical verification before any stronger claim.",
        ]
    )
    Path(f"candidate_symbolic_focus_cover_{focus_r}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def summary_path(focus_r: int) -> Path:
    return Path(f"symbolic_cover_focus_{focus_r}_summary.csv")


def write_summary(
    focus_r: int,
    class_count: int,
    full_count: int,
    partial_count: int,
    uncovered_count: int,
    unknown_count: int,
    selected_count: int,
    remainder_count: int,
    candidate_rule_count: int,
    validation_failures: int,
    verdict: str,
) -> None:
    write_csv(
        summary_path(focus_r),
        [
            "focus_r",
            "total_classes",
            "fully_covered_classes",
            "partially_covered_classes",
            "uncovered_classes",
            "unknown_fullness_classes",
            "selected_rules",
            "symbolic_remainders",
            "candidate_rules_evaluated",
            "validation_failures",
            "verdict",
        ],
        [
            {
                "focus_r": focus_r,
                "total_classes": class_count,
                "fully_covered_classes": full_count,
                "partially_covered_classes": partial_count,
                "uncovered_classes": uncovered_count,
                "unknown_fullness_classes": unknown_count,
                "selected_rules": selected_count,
                "symbolic_remainders": remainder_count,
                "candidate_rules_evaluated": candidate_rule_count,
                "validation_failures": validation_failures,
                "verdict": verdict,
            }
        ],
    )


def selected_rule_counters(focus_r: int) -> tuple[Counter[int], Counter[tuple[int, int]]]:
    path = Path(f"symbolic_cover_focus_{focus_r}_selected_rules.csv")
    d_counter: Counter[int] = Counter()
    pair_counter: Counter[tuple[int, int]] = Counter()
    if not path.exists():
        return d_counter, pair_counter
    for row in read_csv_rows(path):
        d_counter[int(row["d"])] += 1
        pair_counter[(int(row["a"]), int(row["b"]))] += 1
    return d_counter, pair_counter


def compact_counter(counter: Counter[object], limit: int = 5) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{count}" for key, count in counter.most_common(limit))


def run_focus(
    focus_r: int,
    args: argparse.Namespace,
) -> dict[str, object]:
    classes = load_classes(focus_r)
    rules, skipped_rules = load_candidate_rules(
        focus_r=focus_r,
        rule_limit=args.rule_limit,
        summary_rule_limit=args.summary_rule_limit,
        master_rule_limit=args.master_rule_limit,
        max_rule_q=args.max_rule_q,
    )
    coverages = build_rule_coverages(
        focus_r,
        classes,
        rules,
        args.max_refinement_ratio,
    )
    selected = greedy_select_coverages(coverages, len(classes), args.max_selected_rules)
    full_owner, partial_rules, unknown_rules = assign_selected_rules(selected, len(classes))

    validation_failures: list[dict[str, object]] = []
    verified_full_owner: dict[int, Rule] = {}
    for index, rule in full_owner.items():
        failures = verify_full_class(classes[index], rule)
        if failures:
            validation_failures.extend(failures)
            continue
        verified_full_owner[index] = rule

    full_indices = set(verified_full_owner)
    remaining_indices = set(range(len(classes))) - full_indices
    partial_indices = {
        index for index in remaining_indices if partial_rules[index]
    }
    unknown_indices = {
        index for index in remaining_indices if unknown_rules[index]
    }
    uncovered_indices = remaining_indices - partial_indices - unknown_indices

    write_selected_rules(focus_r, selected)
    remainder_count = write_remainders(
        focus_r,
        classes,
        full_indices,
        partial_rules,
        unknown_rules,
    )

    candidate_ready = len(full_indices) == len(classes) and not validation_failures
    verdict = (
        f"candidate symbolic local cover for focus {focus_r}"
        if candidate_ready
        else "not proved yet"
    )
    write_summary(
        focus_r=focus_r,
        class_count=len(classes),
        full_count=len(full_indices),
        partial_count=len(partial_indices),
        uncovered_count=len(uncovered_indices),
        unknown_count=len(unknown_indices),
        selected_count=len(selected),
        remainder_count=remainder_count,
        candidate_rule_count=len(rules),
        validation_failures=len(validation_failures),
        verdict=verdict,
    )
    if candidate_ready:
        write_candidate_focus_file(focus_r, classes, selected)

    d_counter, pair_counter = selected_rule_counters(focus_r)
    print(f"focus residue: {focus_r}")
    print(f"  total unresolved classes read: {len(classes)}")
    print(f"  fully covered: {len(full_indices)}")
    print(f"  partially covered: {len(partial_indices)}")
    print(f"  symbolic remainders: {remainder_count}")
    print(f"  uncovered classes: {len(uncovered_indices)}")
    print(f"  unknown fullness: {len(unknown_indices)}")
    print(f"  selected rules: {len(selected)}")
    print(f"  candidate rules evaluated: {len(rules)}")
    print(f"  skipped rules over q limit or empty residue set: {len(skipped_rules)}")
    print(f"  top d: {compact_counter(d_counter)}")
    print(f"  top pairs: {compact_counter(pair_counter)}")
    print(f"  validation failures: {len(validation_failures)}")
    print(f"  verdict: {verdict}")

    return {
        "focus_r": focus_r,
        "classes": len(classes),
        "full": len(full_indices),
        "partial": len(partial_indices),
        "unknown": len(unknown_indices),
        "uncovered": len(uncovered_indices),
        "remainders": remainder_count,
        "selected": len(selected),
        "validation_failures": len(validation_failures),
        "verdict": verdict,
    }


def report_summary_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for focus_r in FOCUS_RESIDUES:
        path = summary_path(focus_r)
        if path.exists():
            rows.extend(read_csv_rows(path))
    rows.sort(key=lambda row: int(row["focus_r"]))
    return rows


def selected_rule_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for focus_r in FOCUS_RESIDUES:
        path = Path(f"symbolic_cover_focus_{focus_r}_selected_rules.csv")
        if path.exists():
            rows.extend(read_csv_rows(path))
    return rows


def write_report() -> None:
    summaries = report_summary_rows()
    selected_rows = selected_rule_rows()
    selected_d = Counter(int(row["d"]) for row in selected_rows)
    selected_pairs = Counter((int(row["a"]), int(row["b"])) for row in selected_rows)
    selected_rules = Counter(
        (int(row["d"]), int(row["a"]), int(row["b"]), int(row["q"]))
        for row in selected_rows
    )

    lines = [
        "# Symbolic Cover Report",
        "",
        "This report is a research diagnostic. It does not claim a proof of the",
        "Erdos-Straus conjecture and it does not turn partial symbolic coverage",
        "into a proof.",
        "",
        "## Method",
        "",
        "A fixed general-key rule `(d,a,b)` works on a residue set modulo",
        "`q = lcm(4,a,b)`. A recursive unresolved leaf is kept as one class",
        "`n == r (mod m)`. CRT decides whether that class intersects a rule",
        "residue without enumerating all lifted subclasses.",
        "",
        "A class is counted as fully covered only when finite refinement was",
        "checked under the configured ratio limit and sample solutions passed",
        "`check_solution`. Partial intersections become symbolic remainders of",
        "the form `base class AND not S_rule`. Unknown fullness stays a candidate",
        "state, never proof coverage.",
        "",
        "## Focus Runs",
        "",
    ]
    if summaries:
        lines.extend(
            [
                "| focus | classes | full | partial | uncovered | unknown | remainders | rules | validation failures | verdict |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in summaries:
            lines.append(
                f"| {row['focus_r']} | {row['total_classes']} | "
                f"{row['fully_covered_classes']} | {row['partially_covered_classes']} | "
                f"{row['uncovered_classes']} | {row['unknown_fullness_classes']} | "
                f"{row['symbolic_remainders']} | {row['selected_rules']} | "
                f"{row['validation_failures']} | {row['verdict']} |"
            )
    else:
        lines.append("No focus runs have been written yet.")

    lines.extend(
        [
            "",
            "## Master Keys Selected",
            "",
            f"Top selected `d`: `{compact_counter(selected_d, 10)}`.",
            "",
            f"Top selected pairs `(a,b)`: `{compact_counter(selected_pairs, 10)}`.",
            "",
            "| count | d | a | b | q |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for (d, a, b, q), count in selected_rules.most_common(15):
        lines.append(f"| {count} | {d} | {a} | {b} | {q} |")
    if not selected_rules:
        lines.append("| 0 | - | - | - | - |")

    candidate_focuses = [
        row["focus_r"]
        for row in summaries
        if row["verdict"].startswith("candidate symbolic local cover")
    ]
    lines.extend(
        [
            "",
            "## Coverage Boundary",
            "",
            "Fully checked finite coverage appears in the `full` column above.",
            "Symbolic remainders are still open local conditions; they are smaller",
            "descriptions of unresolved work, not closed classes.",
            "",
            "Candidate local focus covers: "
            + (", ".join(candidate_focuses) if candidate_focuses else "none")
            + ".",
            "",
            "Verdict: "
            + (
                "candidate symbolic local cover exists for at least one focus residue; "
                "the full conjecture is still not proved."
                if candidate_focuses
                else "not proved yet."
            ),
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Symbolic cover engine for recursive hard focus leaves."
    )
    parser.add_argument(
        "--focus-residue",
        type=int,
        action="append",
        help="Focus residue to analyze. Repeat to process several; default is all known focuses.",
    )
    parser.add_argument(
        "--max-refinement-ratio",
        type=int,
        default=200_000,
        help="Maximum L/m ratio allowed for exact full-cover checks.",
    )
    parser.add_argument(
        "--rule-limit",
        type=int,
        default=100,
        help="Total symbolic rule candidates evaluated for one focus.",
    )
    parser.add_argument(
        "--summary-rule-limit",
        type=int,
        default=60,
        help="Top rows read from symbolic_rule_summary.csv.",
    )
    parser.add_argument(
        "--master-rule-limit",
        type=int,
        default=80,
        help="Top focus rows read from symbolic_master_keys.csv.",
    )
    parser.add_argument(
        "--max-rule-q",
        type=int,
        default=1_000_000,
        help="Maximum q enumerated when a master-key rule lacks a residue-set CSV row.",
    )
    parser.add_argument(
        "--max-selected-rules",
        type=int,
        default=30,
        help="Greedy rule budget for one focus run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_inputs()
    run_assert_tests()

    focus_residues = args.focus_residue or FOCUS_RESIDUES
    unknown_focuses = [focus_r for focus_r in focus_residues if focus_r not in FOCUS_RESIDUES]
    if unknown_focuses:
        known = ", ".join(str(focus_r) for focus_r in FOCUS_RESIDUES)
        unknown = ", ".join(str(focus_r) for focus_r in unknown_focuses)
        raise SystemExit(f"unknown focus residue(s): {unknown}. Known focus residues: {known}")

    for focus_r in focus_residues:
        run_focus(focus_r, args)
    write_report()


if __name__ == "__main__":
    main()
