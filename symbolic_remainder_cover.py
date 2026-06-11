#!/usr/bin/env python3
"""Iteratively reduce symbolic remainders without explicit lift enumeration.

Input remainders have the form:

    n == r (mod m)
    AND n mod q1 not in S1
    AND n mod q2 not in S2
    ...

This script applies more fixed general-key rules symbolically. A partial hit
adds another exclusion instead of expanding into lifted subresidues. This is a
research diagnostic, not a proof certificate generator.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from erdos_straus import check_solution


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
RULE_RESIDUE_PATH = Path("symbolic_rule_residue_sets.csv")
RULE_SUMMARY_PATH = Path("symbolic_rule_summary.csv")
MASTER_KEYS_PATH = Path("symbolic_master_keys.csv")
REPORT_PATH = Path("symbolic_remainder_cover_report.md")
CONDITION_RE = re.compile(
    r"not\(n mod (?P<q>\d+) in "
    r"S\[d=(?P<d>\d+),a=(?P<a>\d+),b=(?P<b>\d+),size=(?P<size>\d+)\]\)"
)


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
    return int(value) if value not in ("", None) else default


def csv_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else default


def focus_remainder_path(focus_r: int) -> Path:
    return Path(f"symbolic_cover_focus_{focus_r}_remainders.csv")


def focus_selected_rules_path(focus_r: int) -> Path:
    return Path(f"symbolic_cover_focus_{focus_r}_selected_rules.csv")


def required_paths() -> list[Path]:
    paths = [RULE_RESIDUE_PATH, RULE_SUMMARY_PATH, MASTER_KEYS_PATH]
    for focus_r in FOCUS_RESIDUES:
        paths.append(focus_remainder_path(focus_r))
        paths.append(focus_selected_rules_path(focus_r))
    return paths


def ensure_inputs() -> None:
    missing = [path for path in required_paths() if not path.exists()]
    if not missing:
        return
    formatted = "\n".join(f"  - {path}" for path in missing)
    raise SystemExit(f"missing required symbolic remainder inputs:\n{formatted}")


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
    d: int
    a: int
    b: int
    covered_residues: frozenset[int]
    score: float = 0.0
    coverage_ratio: float = 0.0
    source: str = ""

    @property
    def key(self) -> RuleKey:
        return RuleKey(self.d, self.a, self.b)

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)

    @property
    def covered_residue_count(self) -> int:
        return len(self.covered_residues)

    @property
    def pair_sum_ok(self) -> bool:
        return self.a + self.b == 4 * self.d

    def solution_for(self, n: int) -> tuple[int, int, int] | None:
        if not self.pair_sum_ok or (n + self.d) % 4 != 0:
            return None
        product = n * (n + self.d)
        if product % self.a != 0 or product % self.b != 0:
            return None
        return ((n + self.d) // 4, product // self.a, product // self.b)


@dataclass
class SymbolicRemainder:
    focus_r: int
    base_modulus: int
    base_residue: int
    excluded_conditions: dict[int, set[int]] = field(default_factory=dict)
    source_status: str = ""
    empty_reason: str = ""
    partial_reduction_count: int = 0
    unknown_reduction_count: int = 0
    combined_lcm: int = 1
    combined_ratio: int = 1

    def __post_init__(self) -> None:
        self.base_residue %= self.base_modulus
        self.refresh_lcm()

    def refresh_lcm(self) -> None:
        value = self.base_modulus
        for q in self.excluded_conditions:
            value = value * q // math.gcd(value, q)
        self.combined_lcm = value
        self.combined_ratio = value // self.base_modulus

    @property
    def conditions_count(self) -> int:
        return len(self.excluded_conditions)

    def condition_summary(self, max_parts: int = 40) -> str:
        parts: list[str] = []
        for q in sorted(self.excluded_conditions):
            residues = sorted(self.excluded_conditions[q])
            preview = ",".join(str(value) for value in residues[:8])
            if len(residues) > 8:
                preview += ",..."
            parts.append(f"not(n mod {q} in {{{preview}}})")
        if len(parts) > max_parts:
            shown = parts[:max_parts]
            shown.append(f"... {len(parts) - max_parts} more conditions")
            return " AND ".join(shown)
        return " AND ".join(parts)

    def add_exclusion(self, rule: Rule) -> bool:
        before = set(self.excluded_conditions.get(rule.q, set()))
        after = before | set(rule.covered_residues)
        if after == before:
            return False
        self.excluded_conditions[rule.q] = after
        self.refresh_lcm()
        return True

    def satisfies(self, n: int) -> bool:
        if n % self.base_modulus != self.base_residue:
            return False
        return all(n % q not in residues for q, residues in self.excluded_conditions.items())


class ResidueRegistry:
    def __init__(self, max_rule_q: int) -> None:
        self.max_rule_q = max_rule_q
        self.residue_sets: dict[RuleKey, frozenset[int]] = {}
        self.load_rule_residue_csv()

    def load_rule_residue_csv(self) -> None:
        grouped: defaultdict[RuleKey, set[int]] = defaultdict(set)
        for row in read_csv_rows(RULE_RESIDUE_PATH):
            key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
            grouped[key].add(int(row["residue_t"]) % key.q)
        self.residue_sets = {key: frozenset(values) for key, values in grouped.items()}

    def rule_covers_residue(self, key: RuleKey, residue: int) -> bool:
        if key.a + key.b != 4 * key.d:
            return False
        if (residue + key.d) % 4 != 0:
            return False
        product = residue * (residue + key.d)
        return product % key.a == 0 and product % key.b == 0

    def residues_for(self, key: RuleKey) -> frozenset[int] | None:
        if key in self.residue_sets:
            return self.residue_sets[key]
        if key.q > self.max_rule_q:
            return None
        residues = frozenset(
            residue
            for residue in range(key.q)
            if self.rule_covers_residue(key, residue)
        )
        if residues:
            self.residue_sets[key] = residues
        return residues or None


def crt_intersection(m1: int, r1: int, m2: int, r2: int) -> tuple[int, int] | None:
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


def compatible_residues_mod_q(base_modulus: int, base_residue: int, q: int) -> range:
    common = math.gcd(base_modulus, q)
    start = base_residue % common
    return range(start, q, common)


def compatible_rule_residues(remainder: SymbolicRemainder, rule: Rule) -> set[int]:
    common = math.gcd(remainder.base_modulus, rule.q)
    target = remainder.base_residue % common
    excluded_same_q = remainder.excluded_conditions.get(rule.q, set())
    return {
        residue
        for residue in rule.covered_residues
        if residue % common == target and residue not in excluded_same_q
    }


def compatible_count(base_modulus: int, q: int) -> int:
    return q // math.gcd(base_modulus, q)


def allowed_same_q_subset_of_rule(remainder: SymbolicRemainder, rule: Rule) -> bool:
    """Safely detect full coverage visible at the rule modulus.

    The allowed residues modulo rule.q are the base-compatible residues minus
    exclusions already stored at the same modulus. If there are more such
    residues than the rule plus exclusions can possibly account for, the small
    rule residue set cannot cover them all, so we avoid enumerating.
    """
    excluded_same_q = remainder.excluded_conditions.get(rule.q, set())
    count = compatible_count(remainder.base_modulus, rule.q)
    if count > len(rule.covered_residues) + len(excluded_same_q):
        return False
    compatible = set(
        compatible_residues_mod_q(
            remainder.base_modulus,
            remainder.base_residue,
            rule.q,
        )
    )
    allowed = compatible - excluded_same_q
    return bool(allowed) and allowed.issubset(rule.covered_residues)


def exact_allowed_count(remainder: SymbolicRemainder, limit_ratio: int) -> tuple[int | None, str]:
    ratio = remainder.combined_ratio
    if ratio > limit_ratio:
        return None, "combined_refinement_ratio_exceeds_limit"
    allowed = 0
    for offset in range(ratio):
        residue = remainder.base_residue + offset * remainder.base_modulus
        if all(residue % q not in excluded for q, excluded in remainder.excluded_conditions.items()):
            allowed += 1
            if allowed:
                return allowed, "nonempty_exact"
    return 0, "empty_exact"


def simplify_remainder(
    remainder: SymbolicRemainder,
    max_symbolic_refinement_ratio: int,
) -> tuple[bool, str]:
    """Merge conditions, delete no-op exclusions, and detect empty remainders."""
    changed = False
    for q in list(remainder.excluded_conditions):
        residues = {value % q for value in remainder.excluded_conditions[q]}
        common = math.gcd(remainder.base_modulus, q)
        target = remainder.base_residue % common
        residues = {value for value in residues if value % common == target}
        if not residues:
            del remainder.excluded_conditions[q]
            changed = True
            continue

        count = compatible_count(remainder.base_modulus, q)
        if count <= len(residues):
            compatible = set(
                compatible_residues_mod_q(
                    remainder.base_modulus,
                    remainder.base_residue,
                    q,
                )
            )
            if compatible.issubset(residues):
                remainder.empty_reason = (
                    f"condition modulo {q} excludes every base-compatible residue"
                )
                return True, remainder.empty_reason
        remainder.excluded_conditions[q] = residues

    if changed:
        remainder.refresh_lcm()

    exact_count, exact_reason = exact_allowed_count(remainder, max_symbolic_refinement_ratio)
    if exact_count == 0:
        remainder.empty_reason = exact_reason
        return True, exact_reason
    return False, "not_empty_by_available_checks"


def condition_is_impossible(
    remainder: SymbolicRemainder,
    max_symbolic_refinement_ratio: int,
) -> tuple[bool, str]:
    return simplify_remainder(remainder, max_symbolic_refinement_ratio)


@dataclass(frozen=True)
class RuleEvaluation:
    status: str
    reason: str
    refinement_ratio: int | None = None


def evaluate_rule_against_remainder(
    remainder: SymbolicRemainder,
    rule: Rule,
    max_symbolic_refinement_ratio: int,
) -> RuleEvaluation:
    if remainder.empty_reason:
        return RuleEvaluation("empty", remainder.empty_reason)

    touched = compatible_rule_residues(remainder, rule)
    if not touched:
        return RuleEvaluation("covers_nothing", "no_allowed_rule_residue_after_base_and_same_q")

    if allowed_same_q_subset_of_rule(remainder, rule):
        return RuleEvaluation("fully_covers", "all_remaining_same_q_residues_hit_rule")

    if remainder.combined_ratio > max_symbolic_refinement_ratio:
        return RuleEvaluation(
            "symbolic_unknown_fullness",
            "combined_refinement_ratio_exceeds_limit_but_rule_intersects",
            remainder.combined_ratio,
        )

    total_lcm = remainder.combined_lcm * rule.q // math.gcd(remainder.combined_lcm, rule.q)
    ratio = total_lcm // remainder.base_modulus
    if ratio <= max_symbolic_refinement_ratio:
        allowed = 0
        covered = 0
        for offset in range(ratio):
            residue = remainder.base_residue + offset * remainder.base_modulus
            if any(residue % q in excluded for q, excluded in remainder.excluded_conditions.items()):
                continue
            allowed += 1
            if residue % rule.q in rule.covered_residues:
                covered += 1
        if allowed == 0:
            return RuleEvaluation("empty", "exact_refinement_empty", ratio)
        if covered == 0:
            return RuleEvaluation("covers_nothing", "exact_refinement_no_covered_residue", ratio)
        if covered == allowed:
            return RuleEvaluation("fully_covers", "exact_refinement_all_allowed_residues_covered", ratio)
        return RuleEvaluation("partially_covers", "exact_refinement_some_residues_covered", ratio)

    return RuleEvaluation(
        "symbolic_unknown_fullness",
        "combined_refinement_ratio_exceeds_limit_but_rule_intersects",
        ratio,
    )


def parse_condition_summary(
    summary: str,
    registry: ResidueRegistry,
) -> dict[int, set[int]]:
    conditions: defaultdict[int, set[int]] = defaultdict(set)
    for match in CONDITION_RE.finditer(summary or ""):
        key = RuleKey(
            int(match.group("d")),
            int(match.group("a")),
            int(match.group("b")),
        )
        q = int(match.group("q"))
        if q != key.q:
            continue
        residues = registry.residues_for(key)
        if residues is None:
            continue
        conditions[q].update(residues)
    return {q: set(values) for q, values in conditions.items()}


def load_remainders(
    focus_r: int,
    registry: ResidueRegistry,
    max_symbolic_refinement_ratio: int,
) -> tuple[list[SymbolicRemainder], list[SymbolicRemainder]]:
    active: list[SymbolicRemainder] = []
    empty: list[SymbolicRemainder] = []
    parsed_cache: dict[str, dict[int, set[int]]] = {}
    for row in read_csv_rows(focus_remainder_path(focus_r)):
        summary = row.get("condition_summary", "")
        if summary not in parsed_cache:
            parsed_cache[summary] = parse_condition_summary(summary, registry)
        remainder = SymbolicRemainder(
            focus_r=focus_r,
            base_modulus=int(row["base_modulus"]),
            base_residue=int(row["base_residue"]),
            excluded_conditions={
                q: set(residues)
                for q, residues in parsed_cache[summary].items()
            },
            source_status=row.get("status", ""),
        )
        is_empty, reason = condition_is_impossible(remainder, max_symbolic_refinement_ratio)
        if is_empty:
            remainder.empty_reason = reason
            empty.append(remainder)
        else:
            active.append(remainder)
    return active, empty


def add_rule_score(
    scores: Counter[RuleKey],
    ratios: dict[RuleKey, float],
    sources: defaultdict[RuleKey, set[str]],
    key: RuleKey,
    score: float,
    ratio: float,
    source: str,
) -> None:
    scores[key] += score
    ratios[key] = max(ratios.get(key, 0.0), ratio)
    sources[key].add(source)


def load_candidate_rules(
    focus_r: int,
    registry: ResidueRegistry,
    max_candidate_rules: int,
) -> list[Rule]:
    scores: Counter[RuleKey] = Counter()
    ratios: dict[RuleKey, float] = {}
    sources: defaultdict[RuleKey, set[str]] = defaultdict(set)
    already_applied: set[RuleKey] = set()

    for row in read_csv_rows(focus_selected_rules_path(focus_r)):
        already_applied.add(RuleKey(int(row["d"]), int(row["a"]), int(row["b"])))

    for row in read_csv_rows(RULE_SUMMARY_PATH):
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        add_rule_score(
            scores,
            ratios,
            sources,
            key,
            csv_int(row, "diagnostic_leaf_count", 1),
            csv_float(row, "coverage_ratio"),
            "rule_summary",
        )

    for row in read_csv_rows(MASTER_KEYS_PATH):
        if csv_int(row, "focus_r") != focus_r:
            continue
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        if key in already_applied:
            continue
        add_rule_score(
            scores,
            ratios,
            sources,
            key,
            csv_int(row, "count", 1),
            0.0,
            f"master_keys_focus_{focus_r}",
        )

    rules: list[Rule] = []
    for key, score in scores.most_common():
        if key in already_applied:
            continue
        residues = registry.residues_for(key)
        if residues is None:
            continue
        rules.append(
            Rule(
                d=key.d,
                a=key.a,
                b=key.b,
                covered_residues=residues,
                score=float(score),
                coverage_ratio=ratios.get(key, 0.0),
                source=";".join(sorted(sources[key])),
            )
        )
        if len(rules) >= max_candidate_rules:
            break
    return rules


@dataclass
class RuleBitsets:
    full_bits: int
    touch_bits: int
    unknown_bits: int


def bit_count(value: int) -> int:
    return value.bit_count()


def build_rule_bitsets(
    remainders: list[SymbolicRemainder],
    rules: list[Rule],
    max_symbolic_refinement_ratio: int,
) -> dict[RuleKey, RuleBitsets]:
    bitsets: dict[RuleKey, RuleBitsets] = {}
    for rule in rules:
        full_bits = 0
        touch_bits = 0
        unknown_bits = 0
        for index, remainder in enumerate(remainders):
            evaluation = evaluate_rule_against_remainder(
                remainder,
                rule,
                max_symbolic_refinement_ratio,
            )
            if evaluation.status == "fully_covers":
                full_bits |= 1 << index
                touch_bits |= 1 << index
            elif evaluation.status == "partially_covers":
                touch_bits |= 1 << index
            elif evaluation.status == "symbolic_unknown_fullness":
                unknown_bits |= 1 << index
                touch_bits |= 1 << index
        bitsets[rule.key] = RuleBitsets(full_bits, touch_bits, unknown_bits)
    return bitsets


def choose_rule(
    rules: list[Rule],
    bitsets: dict[RuleKey, RuleBitsets],
    active_bits: int,
    selected: set[RuleKey],
) -> tuple[Rule | None, tuple[int, int, int, float]]:
    best_rule: Rule | None = None
    best_score = (0, 0, 0, 0.0)
    for rule in rules:
        if rule.key in selected:
            continue
        rule_bits = bitsets[rule.key]
        full_count = bit_count(rule_bits.full_bits & active_bits)
        touch_count = bit_count(rule_bits.touch_bits & active_bits)
        unknown_count = bit_count(rule_bits.unknown_bits & active_bits)
        partial_count = max(touch_count - full_count, 0)
        score = (
            full_count,
            partial_count,
            -rule.q,
            rule.coverage_ratio,
        )
        if touch_count == 0:
            continue
        if score > best_score:
            best_score = score
            best_rule = rule
    return best_rule, best_score


def find_samples(
    remainder: SymbolicRemainder,
    max_samples: int,
    search_steps: int,
) -> list[int]:
    samples: list[int] = []
    for offset in range(search_steps):
        n = remainder.base_residue + offset * remainder.base_modulus
        if n <= 1:
            continue
        if remainder.satisfies(n):
            samples.append(n)
            if len(samples) >= max_samples:
                break
    return samples


def verify_rule_on_remainder(
    remainder: SymbolicRemainder,
    rule: Rule,
    sample_search_steps: int,
) -> tuple[bool, str]:
    samples = find_samples(remainder, 3, sample_search_steps)
    if not samples:
        return False, "no_sample_satisfying_remainder_conditions_found"
    for n in samples:
        solution = rule.solution_for(n)
        if solution is None or not check_solution(n, *solution):
            return False, f"check_solution_failed_for_n_{n}"
    return True, "sample_verification_passed"


def apply_rule(
    rule: Rule,
    remainders: list[SymbolicRemainder],
    active_indices: set[int],
    max_symbolic_refinement_ratio: int,
    sample_search_steps: int,
) -> tuple[set[int], dict[str, int], list[dict[str, object]], list[SymbolicRemainder]]:
    next_active = set(active_indices)
    stats = Counter()
    failures: list[dict[str, object]] = []
    new_empty: list[SymbolicRemainder] = []

    for index in list(active_indices):
        remainder = remainders[index]
        evaluation = evaluate_rule_against_remainder(
            remainder,
            rule,
            max_symbolic_refinement_ratio,
        )
        if evaluation.status == "empty":
            next_active.discard(index)
            stats["empty_after_application"] += 1
            remainder.empty_reason = evaluation.reason
            new_empty.append(remainder)
            continue
        if evaluation.status == "covers_nothing":
            continue
        if evaluation.status == "fully_covers":
            ok, reason = verify_rule_on_remainder(remainder, rule, sample_search_steps)
            if ok:
                next_active.discard(index)
                stats["fully_covered"] += 1
            else:
                failures.append(
                    {
                        "focus_r": remainder.focus_r,
                        "base_modulus": remainder.base_modulus,
                        "base_residue": remainder.base_residue,
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                        "reason": reason,
                    }
                )
            continue

        changed = remainder.add_exclusion(rule)
        if evaluation.status == "symbolic_unknown_fullness":
            remainder.unknown_reduction_count += int(changed)
            stats["unknown_fullness"] += int(changed)
        else:
            remainder.partial_reduction_count += int(changed)
            stats["partially_reduced"] += int(changed)

        is_empty, reason = condition_is_impossible(remainder, max_symbolic_refinement_ratio)
        if is_empty:
            next_active.discard(index)
            stats["empty_after_application"] += 1
            remainder.empty_reason = reason
            new_empty.append(remainder)

    return next_active, dict(stats), failures, new_empty


def write_empty_remainders(focus_r: int, empty_remainders: list[SymbolicRemainder]) -> None:
    rows = [
        {
            "focus_r": remainder.focus_r,
            "base_modulus": remainder.base_modulus,
            "base_residue": remainder.base_residue,
            "conditions_count": remainder.conditions_count,
            "condition_summary": remainder.condition_summary(),
            "why_impossible": remainder.empty_reason,
        }
        for remainder in empty_remainders
    ]
    write_csv(
        Path(f"symbolic_empty_remainders_{focus_r}.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "conditions_count",
            "condition_summary",
            "why_impossible",
        ],
        rows,
    )


def write_remaining(focus_r: int, remainders: list[SymbolicRemainder], active_indices: set[int]) -> None:
    rows = []
    for index in sorted(active_indices):
        remainder = remainders[index]
        status = (
            "symbolic_unknown_fullness"
            if remainder.unknown_reduction_count
            else "symbolic_remainder"
        )
        rows.append(
            {
                "focus_r": remainder.focus_r,
                "base_modulus": remainder.base_modulus,
                "base_residue": remainder.base_residue,
                "conditions_count": remainder.conditions_count,
                "condition_summary": remainder.condition_summary(),
                "status": status,
            }
        )
    write_csv(
        Path(f"symbolic_remainder_focus_{focus_r}_remaining.csv"),
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


def write_selected_rules(focus_r: int, rows: list[dict[str, object]]) -> None:
    write_csv(
        Path(f"symbolic_remainder_focus_{focus_r}_selected_rules.csv"),
        [
            "iteration",
            "focus_r",
            "d",
            "a",
            "b",
            "q",
            "covered_residue_count",
            "fully_covered_count",
            "partial_count",
            "empty_after_application_count",
            "unknown_fullness_count",
        ],
        rows,
    )


def write_iteration_log(focus_r: int, rows: list[dict[str, object]]) -> None:
    write_csv(
        Path(f"symbolic_remainder_focus_{focus_r}_iteration_log.csv"),
        [
            "iteration",
            "focus_r",
            "active_before",
            "active_after",
            "d",
            "a",
            "b",
            "q",
            "fully_covered",
            "partially_reduced",
            "unknown_fullness",
            "empty_after_application",
            "validation_failures",
            "score_full",
            "score_partial",
            "score_negative_q",
            "score_coverage_ratio",
        ],
        rows,
    )


def write_summary(
    focus_r: int,
    initial_remainders: int,
    empty_remainders_removed: int,
    fully_covered_remainders: int,
    partially_reduced_remainders: int,
    remaining_remainders: int,
    unknown_fullness: int,
    selected_rules: int,
    validation_failures: int,
    verdict: str,
) -> None:
    write_csv(
        Path(f"symbolic_remainder_focus_{focus_r}_summary.csv"),
        [
            "focus_r",
            "initial_remainders",
            "empty_remainders_removed",
            "fully_covered_remainders",
            "partially_reduced_remainders",
            "remaining_remainders",
            "unknown_fullness",
            "selected_rules",
            "validation_failures",
            "verdict",
        ],
        [
            {
                "focus_r": focus_r,
                "initial_remainders": initial_remainders,
                "empty_remainders_removed": empty_remainders_removed,
                "fully_covered_remainders": fully_covered_remainders,
                "partially_reduced_remainders": partially_reduced_remainders,
                "remaining_remainders": remaining_remainders,
                "unknown_fullness": unknown_fullness,
                "selected_rules": selected_rules,
                "validation_failures": validation_failures,
                "verdict": verdict,
            }
        ],
    )


def write_candidate_file(focus_r: int, selected_rows: list[dict[str, object]]) -> None:
    lines = [
        f"# Candidate Symbolic Remainder Cover for {focus_r}",
        "",
        "This is a candidate symbolic local cover for one focus residue class,",
        "not a proof of the full Erdos-Straus conjecture.",
        "",
        "All symbolic remainders for this focus were removed by fully checked",
        "coverage or by detected empty conditions, with sample verification.",
        "",
        "| iteration | d | a | b | q | fully covered | empty after application |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in selected_rows:
        lines.append(
            f"| {row['iteration']} | {row['d']} | {row['a']} | {row['b']} | "
            f"{row['q']} | {row['fully_covered_count']} | "
            f"{row['empty_after_application_count']} |"
        )
    lines.extend(
        [
            "",
            "Needs independent mathematical verification before any stronger claim.",
        ]
    )
    Path(f"candidate_symbolic_remainder_cover_{focus_r}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def compact_counter(counter: Counter[object], limit: int = 10) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{count}" for key, count in counter.most_common(limit))


def run_focus(focus_r: int, args: argparse.Namespace) -> dict[str, object]:
    registry = ResidueRegistry(args.max_rule_q)
    remainders, initially_empty = load_remainders(
        focus_r,
        registry,
        args.max_symbolic_refinement_ratio,
    )
    rules = load_candidate_rules(focus_r, registry, args.max_candidate_rules)
    bitsets = build_rule_bitsets(remainders, rules, args.max_symbolic_refinement_ratio)

    active_indices = set(range(len(remainders)))
    active_bits = (1 << len(remainders)) - 1 if remainders else 0
    selected_keys: set[RuleKey] = set()
    selected_rows: list[dict[str, object]] = []
    iteration_rows: list[dict[str, object]] = []
    all_empty = list(initially_empty)
    validation_failures: list[dict[str, object]] = []
    fully_covered_total = 0
    partial_touched_indices: set[int] = set()
    unknown_touched_indices: set[int] = set()

    for iteration in range(1, args.max_iterations + 1):
        rule, score = choose_rule(rules, bitsets, active_bits, selected_keys)
        if rule is None:
            break

        active_before = len(active_indices)
        next_active, stats, failures, new_empty = apply_rule(
            rule,
            remainders,
            active_indices,
            args.max_symbolic_refinement_ratio,
            args.sample_search_steps,
        )
        selected_keys.add(rule.key)
        validation_failures.extend(failures)
        all_empty.extend(new_empty)

        fully = stats.get("fully_covered", 0)
        partial = stats.get("partially_reduced", 0)
        unknown = stats.get("unknown_fullness", 0)
        empty_after = stats.get("empty_after_application", 0)
        if fully == 0 and partial == 0 and unknown == 0 and empty_after == 0:
            continue

        # Track unique remainders that received symbolic reductions.
        removed = active_indices - next_active
        for index in active_indices - removed:
            if remainders[index].partial_reduction_count:
                partial_touched_indices.add(index)
            if remainders[index].unknown_reduction_count:
                unknown_touched_indices.add(index)

        active_indices = next_active
        active_bits = 0
        for index in active_indices:
            active_bits |= 1 << index

        fully_covered_total += fully
        selected_row = {
            "iteration": iteration,
            "focus_r": focus_r,
            "d": rule.d,
            "a": rule.a,
            "b": rule.b,
            "q": rule.q,
            "covered_residue_count": rule.covered_residue_count,
            "fully_covered_count": fully,
            "partial_count": partial,
            "empty_after_application_count": empty_after,
            "unknown_fullness_count": unknown,
        }
        selected_rows.append(selected_row)
        iteration_rows.append(
            {
                "iteration": iteration,
                "focus_r": focus_r,
                "active_before": active_before,
                "active_after": len(active_indices),
                "d": rule.d,
                "a": rule.a,
                "b": rule.b,
                "q": rule.q,
                "fully_covered": fully,
                "partially_reduced": partial,
                "unknown_fullness": unknown,
                "empty_after_application": empty_after,
                "validation_failures": len(failures),
                "score_full": score[0],
                "score_partial": score[1],
                "score_negative_q": score[2],
                "score_coverage_ratio": score[3],
            }
        )
        if not active_indices:
            break

    remaining_count = len(active_indices)
    unknown_count = len(unknown_touched_indices)
    verdict = (
        f"candidate symbolic local cover for focus {focus_r}"
        if remaining_count == 0 and not validation_failures and unknown_count == 0
        else "not proved yet"
    )

    write_selected_rules(focus_r, selected_rows)
    write_iteration_log(focus_r, iteration_rows)
    write_remaining(focus_r, remainders, active_indices)
    write_empty_remainders(focus_r, all_empty)
    write_summary(
        focus_r=focus_r,
        initial_remainders=len(remainders) + len(initially_empty),
        empty_remainders_removed=len(all_empty),
        fully_covered_remainders=fully_covered_total,
        partially_reduced_remainders=len(partial_touched_indices),
        remaining_remainders=remaining_count,
        unknown_fullness=unknown_count,
        selected_rules=len(selected_rows),
        validation_failures=len(validation_failures),
        verdict=verdict,
    )
    if verdict.startswith("candidate symbolic local cover"):
        write_candidate_file(focus_r, selected_rows)

    d_counter = Counter(row["d"] for row in selected_rows)
    pair_counter = Counter((row["a"], row["b"]) for row in selected_rows)
    print(f"focus residue: {focus_r}")
    print(f"  initial remainders: {len(remainders) + len(initially_empty)}")
    print(f"  initially empty removed: {len(initially_empty)}")
    print(f"  fully covered remainders: {fully_covered_total}")
    print(f"  partially reduced remainders: {len(partial_touched_indices)}")
    print(f"  remaining remainders: {remaining_count}")
    print(f"  unknown fullness remainders: {unknown_count}")
    print(f"  empty remainders removed total: {len(all_empty)}")
    print(f"  selected rules: {len(selected_rows)}")
    print(f"  validation failures: {len(validation_failures)}")
    print(f"  top d: {compact_counter(d_counter)}")
    print(f"  top pairs: {compact_counter(pair_counter)}")
    print(f"  verdict: {verdict}")

    return {
        "focus_r": focus_r,
        "initial": len(remainders) + len(initially_empty),
        "empty": len(all_empty),
        "full": fully_covered_total,
        "partial": len(partial_touched_indices),
        "remaining": remaining_count,
        "unknown": unknown_count,
        "selected": len(selected_rows),
        "validation_failures": len(validation_failures),
        "verdict": verdict,
        "top_d": compact_counter(d_counter, 5),
        "top_pairs": compact_counter(pair_counter, 5),
    }


def summary_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for focus_r in FOCUS_RESIDUES:
        path = Path(f"symbolic_remainder_focus_{focus_r}_summary.csv")
        if path.exists():
            rows.extend(read_csv_rows(path))
    rows.sort(key=lambda row: int(row["focus_r"]))
    return rows


def selected_rule_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for focus_r in FOCUS_RESIDUES:
        path = Path(f"symbolic_remainder_focus_{focus_r}_selected_rules.csv")
        if path.exists():
            rows.extend(read_csv_rows(path))
    return rows


def write_report() -> None:
    summaries = summary_rows()
    selected = selected_rule_rows()
    d_counter = Counter(int(row["d"]) for row in selected)
    pair_counter = Counter((int(row["a"]), int(row["b"])) for row in selected)
    candidate_focuses = [
        row["focus_r"]
        for row in summaries
        if row["verdict"].startswith("candidate symbolic local cover")
    ]

    lines = [
        "# Symbolic Remainder Cover Report",
        "",
        "This report is a research diagnostic. It does not claim a proof of the",
        "Erdos-Straus conjecture and it does not create a proof certificate.",
        "",
        "## Method",
        "",
        "Symbolic remainders keep the unresolved space as a base congruence plus",
        "negative residue-set conditions. Applying a new fixed rule either removes",
        "a fully covered remainder, adds another negative condition to a partial",
        "remainder, or records unknown fullness when exact refinement would be too",
        "large. No huge lifted subresidue tree is materialized.",
        "",
            "Partial coverage and unknown fullness are not proof coverage.",
            "The `unknown` column counts unique remainders that received at least",
            "one symbolic reduction whose exact full/partial status exceeded the",
            "configured refinement-ratio limit; it can overlap with later full",
            "removals and should be read as a diagnostic warning, not progress",
            "toward a proof.",
            "",
            "## Focus Results",
        "",
    ]
    if summaries:
        lines.extend(
            [
                "| focus | initial | empty removed | full | partial reduced | remaining | unknown | rules | validation failures | verdict |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in summaries:
            lines.append(
                f"| {row['focus_r']} | {row['initial_remainders']} | "
                f"{row['empty_remainders_removed']} | {row['fully_covered_remainders']} | "
                f"{row['partially_reduced_remainders']} | {row['remaining_remainders']} | "
                f"{row['unknown_fullness']} | {row['selected_rules']} | "
                f"{row['validation_failures']} | {row['verdict']} |"
            )
    else:
        lines.append("No focus runs have been written yet.")

    lines.extend(
        [
            "",
            "## Main Rules",
            "",
            f"Top selected `d`: `{compact_counter(d_counter)}`.",
            "",
            f"Top selected pairs `(a,b)`: `{compact_counter(pair_counter)}`.",
            "",
            "## Interpretation",
            "",
            "A large number of remaining classes receiving additional negative",
            "conditions is evidence that symbolic compression is useful. It is not",
            "a proof unless the remaining count reaches zero with no validation",
            "failures and no unknown-fullness coverage.",
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
        description="Reduce symbolic remainders with additional fixed rules."
    )
    parser.add_argument(
        "--focus-residue",
        type=int,
        action="append",
        help="Focus residue to process. Repeat for multiple; default is all known focuses.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum greedy rule applications per focus.",
    )
    parser.add_argument(
        "--max-candidate-rules",
        type=int,
        default=500,
        help="Maximum candidate rules loaded from summary/master/selected files.",
    )
    parser.add_argument(
        "--max-symbolic-refinement-ratio",
        type=int,
        default=500_000,
        help="Maximum L/base_modulus ratio for exact symbolic checks.",
    )
    parser.add_argument(
        "--max-rule-q",
        type=int,
        default=1_000_000,
        help="Maximum q enumerated when building missing rule residue sets.",
    )
    parser.add_argument(
        "--sample-search-steps",
        type=int,
        default=20_000,
        help="Number of base-class samples to scan for fully covered verification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_inputs()
    run_assert_tests()

    focus_residues = args.focus_residue or FOCUS_RESIDUES
    unknown_focuses = [focus_r for focus_r in focus_residues if focus_r not in FOCUS_RESIDUES]
    if unknown_focuses:
        known = ", ".join(str(value) for value in FOCUS_RESIDUES)
        unknown = ", ".join(str(value) for value in unknown_focuses)
        raise SystemExit(f"unknown focus residue(s): {unknown}. Known focus residues: {known}")

    for focus_r in focus_residues:
        run_focus(focus_r, args)
    write_report()


if __name__ == "__main__":
    main()
