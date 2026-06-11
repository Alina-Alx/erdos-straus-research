#!/usr/bin/env python3
"""Analyze relations between negative symbolic conditions.

Remainders look like:

    n == r (mod m)
    AND n mod q1 not in S1
    AND n mod q2 not in S2

This script studies whether visible negative conditions imply each other,
contradict each other, or force a fixed general-key rule. It is deliberately
bounded by refinement-ratio limits and does not create a proof certificate.
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


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
REMAINDER_PATHS = {
    focus_r: Path(f"symbolic_remainder_focus_{focus_r}_remaining.csv")
    for focus_r in FOCUS_RESIDUES
}
OPTIONAL_INPUTS = [
    Path("symbolic_rule_residue_sets.csv"),
    Path("symbolic_rule_summary.csv"),
    Path("symbolic_master_keys.csv"),
    Path("remaining_sample_minimal_rules.csv"),
    Path("candidate_lemma_tests.csv"),
]
CONDITION_RE = re.compile(
    r"not\(n mod (?P<q>\d+) in "
    r"(?:\{(?P<brace_residues>[^}]*)\}|"
    r"S\[d=(?P<d>\d+),a=(?P<a>\d+),b=(?P<b>\d+),size=(?P<size>\d+)\])"
    r"\)"
)


@dataclass(frozen=True)
class BaseClass:
    focus_r: int
    modulus: int
    residue: int

    @property
    def normalized_residue(self) -> int:
        return self.residue % self.modulus

    @property
    def text(self) -> str:
        return f"{self.normalized_residue} mod {self.modulus}"


@dataclass(frozen=True)
class RuleKey:
    d: int
    a: int
    b: int

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)

    @property
    def text(self) -> str:
        return f"d={self.d},a={self.a},b={self.b}"


@dataclass
class NegativeCondition:
    q: int
    excluded_set: frozenset[int]
    source_rule: RuleKey | None = None

    @property
    def signature(self) -> tuple[int, tuple[int, ...]]:
        return (self.q, tuple(sorted(self.excluded_set)))

    @property
    def text(self) -> str:
        values = ",".join(str(value) for value in sorted(self.excluded_set)[:8])
        if len(self.excluded_set) > 8:
            values += ",..."
        return f"n mod {self.q} not in {{{values}}}"


@dataclass
class Remainder:
    base_class: BaseClass
    conditions: list[NegativeCondition]
    original_conditions_count: int
    visible_truncated: bool
    source_status: str = ""


@dataclass(frozen=True)
class PairRelation:
    status: str
    a_implies_b: bool = False
    b_implies_a: bool = False
    contradiction: bool = False
    remaining_count: int | None = None
    ratio: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class ImplicationResult:
    status: str
    implied: bool
    minimal_conditions: tuple[NegativeCondition, ...] = ()
    ratio: int | None = None
    tested_residue_count: int | None = None
    counterexample_residue: int | None = None
    reason: str = ""


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


def int_or_zero(value: str | None) -> int:
    return int(value) if value not in ("", None) else 0


def factorization(value: int) -> tuple[tuple[int, int], ...]:
    if value <= 1:
        return ()
    n = value
    factors: list[tuple[int, int]] = []
    exponent = 0
    while n % 2 == 0:
        exponent += 1
        n //= 2
    if exponent:
        factors.append((2, exponent))
    divisor = 3
    while divisor * divisor <= n:
        exponent = 0
        while n % divisor == 0:
            exponent += 1
            n //= divisor
        if exponent:
            factors.append((divisor, exponent))
        divisor += 2
    if n > 1:
        factors.append((n, 1))
    return tuple(factors)


def prime_factors(value: int) -> tuple[int, ...]:
    return tuple(prime for prime, _ in factorization(value))


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
    assert crt_intersection(5, 4, 5, 4) == (5, 4)
    assert crt_intersection(12, 9, 4, 1) == (12, 9)
    assert crt_intersection(8, 5, 4, 1) == (8, 5)


def evenly_sample_rows(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if limit <= 0 or len(rows) <= limit:
        return rows
    if limit == 1:
        return [rows[0]]
    step = (len(rows) - 1) / (limit - 1)
    return [rows[round(index * step)] for index in range(limit)]


def parse_condition_summary(
    summary: str,
    rule_by_signature: dict[tuple[int, tuple[int, ...]], RuleKey],
) -> tuple[list[NegativeCondition], bool]:
    grouped: defaultdict[int, set[int]] = defaultdict(set)
    explicit_rule: dict[int, RuleKey] = {}

    for match in CONDITION_RE.finditer(summary or ""):
        q = int(match.group("q"))
        residues_text = match.group("brace_residues")
        if residues_text is not None:
            for part in residues_text.split(","):
                part = part.strip()
                if not part or part == "...":
                    continue
                try:
                    grouped[q].add(int(part) % q)
                except ValueError:
                    continue
        elif match.group("d"):
            rule = RuleKey(int(match.group("d")), int(match.group("a")), int(match.group("b")))
            explicit_rule[q] = rule

    conditions: list[NegativeCondition] = []
    for q, residues in sorted(grouped.items()):
        signature = (q, tuple(sorted(residues)))
        source_rule = explicit_rule.get(q) or rule_by_signature.get(signature)
        conditions.append(NegativeCondition(q=q, excluded_set=frozenset(residues), source_rule=source_rule))
    return conditions, "..." in (summary or "")


def load_rule_residue_sets() -> tuple[dict[RuleKey, set[int]], dict[tuple[int, tuple[int, ...]], RuleKey]]:
    path = Path("symbolic_rule_residue_sets.csv")
    if not path.exists():
        return {}, {}
    grouped: defaultdict[RuleKey, set[int]] = defaultdict(set)
    for row in read_csv_rows(path):
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        grouped[key].add(int(row["residue_t"]) % key.q)
    rule_sets = dict(grouped)
    by_signature: dict[tuple[int, tuple[int, ...]], RuleKey] = {}
    for key, residues in rule_sets.items():
        by_signature[(key.q, tuple(sorted(residues)))] = key
    return rule_sets, by_signature


def rule_covers_residue(rule: RuleKey, residue: int) -> bool:
    if rule.a + rule.b != 4 * rule.d:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def build_rule_residue_set(rule: RuleKey, max_rule_q: int) -> set[int] | None:
    if rule.q > max_rule_q:
        return None
    return {residue for residue in range(rule.q) if rule_covers_residue(rule, residue)}


def compatible_residue_count(modulus: int, q: int) -> int:
    return q // math.gcd(modulus, q)


def all_compatible_residues_in_set(modulus: int, residue: int, q: int, values: frozenset[int] | set[int]) -> bool:
    common = math.gcd(modulus, q)
    count = q // common
    if count > len(values):
        return False
    target = residue % common
    return all(candidate in values for candidate in range(target, q, common))


def condition_empty_over_base(base: BaseClass, condition: NegativeCondition) -> bool:
    return all_compatible_residues_in_set(
        base.modulus,
        base.normalized_residue,
        condition.q,
        condition.excluded_set,
    )


def negative_condition_implies(base: BaseClass, antecedent: NegativeCondition, consequent: NegativeCondition) -> bool:
    """Check C AND antecedent => consequent without full LCM enumeration.

    A negative condition is true when n mod q is outside its excluded set. The
    implication fails exactly when consequent is false and antecedent is true.
    We only need to examine the small excluded set of the consequent.
    """
    any_consequent_false_compatible = False
    for consequent_residue in consequent.excluded_set:
        intersection = crt_intersection(
            base.modulus,
            base.normalized_residue,
            consequent.q,
            consequent_residue,
        )
        if intersection is None:
            continue
        any_consequent_false_compatible = True
        modulus, residue = intersection
        if not all_compatible_residues_in_set(
            modulus,
            residue,
            antecedent.q,
            antecedent.excluded_set,
        ):
            return False
    return True if any_consequent_false_compatible else True


def load_remainders(sample_limit: int, rule_by_signature: dict[tuple[int, tuple[int, ...]], RuleKey]) -> tuple[list[Remainder], list[Path], bool]:
    missing = [path for path in REMAINDER_PATHS.values() if not path.exists()]
    remainders: list[Remainder] = []
    sampled = bool(sample_limit)
    per_focus_limit = sample_limit // len(FOCUS_RESIDUES) if sample_limit else 0

    for focus_r, path in REMAINDER_PATHS.items():
        if not path.exists():
            continue
        rows = read_csv_rows(path)
        if per_focus_limit:
            rows = evenly_sample_rows(rows, per_focus_limit)
        for row in rows:
            conditions, truncated = parse_condition_summary(row.get("condition_summary", ""), rule_by_signature)
            remainders.append(
                Remainder(
                    base_class=BaseClass(
                        focus_r=focus_r,
                        modulus=int(row["base_modulus"]),
                        residue=int(row["base_residue"]),
                    ),
                    conditions=conditions,
                    original_conditions_count=int(row["conditions_count"]),
                    visible_truncated=truncated,
                    source_status=row.get("status", ""),
                )
            )
    return remainders, missing, sampled


def load_candidate_rules(rule_sets: dict[RuleKey, set[int]], max_candidate_rules: int, max_rule_q: int) -> list[tuple[RuleKey, set[int], int]]:
    scores: Counter[RuleKey] = Counter()
    for rule, residues in rule_sets.items():
        scores[rule] += max(len(residues), 1)

    for path in (Path("symbolic_rule_summary.csv"), Path("symbolic_master_keys.csv"), Path("remaining_sample_minimal_rules.csv")):
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            if not row.get("d") or not row.get("a") or not row.get("b"):
                continue
            rule = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
            weight = (
                int_or_zero(row.get("diagnostic_leaf_count"))
                or int_or_zero(row.get("count"))
                or 1
            )
            scores[rule] += weight

    candidates: list[tuple[RuleKey, set[int], int]] = []
    for rule, score in scores.most_common():
        residues = rule_sets.get(rule)
        if residues is None:
            residues = build_rule_residue_set(rule, max_rule_q)
        if not residues:
            continue
        candidates.append((rule, residues, score))
        if len(candidates) >= max_candidate_rules:
            break
    return candidates


def relation_for_pair(
    base: BaseClass,
    a: NegativeCondition,
    b: NegativeCondition,
    max_ratio: int,
    small_threshold: int,
    max_enumerated_residues: int,
) -> PairRelation:
    L = lcm_many(base.modulus, a.q, b.q)
    ratio = L // base.modulus
    analytic_a_implies_b = negative_condition_implies(base, a, b)
    analytic_b_implies_a = negative_condition_implies(base, b, a)
    if ratio > max_ratio or ratio > max_enumerated_residues:
        if condition_empty_over_base(base, a) or condition_empty_over_base(base, b):
            return PairRelation(
                status="contradiction",
                a_implies_b=analytic_a_implies_b,
                b_implies_a=analytic_b_implies_a,
                contradiction=True,
                remaining_count=0,
                ratio=ratio,
                reason="one_negative_condition_empty_over_base",
            )
        if analytic_a_implies_b and analytic_b_implies_a:
            return PairRelation(status="equivalent", a_implies_b=True, b_implies_a=True, ratio=ratio, reason="analytic_implication_without_full_enumeration")
        if analytic_a_implies_b:
            return PairRelation(status="a_implies_b", a_implies_b=True, ratio=ratio, reason="analytic_implication_without_full_enumeration")
        if analytic_b_implies_a:
            return PairRelation(status="b_implies_a", b_implies_a=True, ratio=ratio, reason="analytic_implication_without_full_enumeration")
        return PairRelation(status="symbolic_too_large", ratio=ratio, reason="pair_refinement_ratio_or_enumeration_budget_exceeds_limit")

    a_implies_b = True
    b_implies_a = True
    both_count = 0
    allowed_count = 0
    for offset in range(ratio):
        residue = (base.normalized_residue + offset * base.modulus) % L
        a_ok = residue % a.q not in a.excluded_set
        b_ok = residue % b.q not in b.excluded_set
        if a_ok:
            allowed_count += 1
        if a_ok and not b_ok:
            a_implies_b = False
        if b_ok and not a_ok:
            b_implies_a = False
        if a_ok and b_ok:
            both_count += 1

    if both_count == 0:
        return PairRelation(
            status="contradiction",
            a_implies_b=a_implies_b,
            b_implies_a=b_implies_a,
            contradiction=True,
            remaining_count=0,
            ratio=ratio,
            reason="base_and_both_negative_conditions_empty",
        )
    if a_implies_b and b_implies_a:
        status = "equivalent"
    elif a_implies_b:
        status = "a_implies_b"
    elif b_implies_a:
        status = "b_implies_a"
    elif both_count <= small_threshold:
        status = "small_remaining_pair"
    else:
        status = "independent"
    return PairRelation(
        status=status,
        a_implies_b=a_implies_b,
        b_implies_a=b_implies_a,
        contradiction=False,
        remaining_count=both_count,
        ratio=ratio,
        reason=f"allowed_after_a={allowed_count}",
    )


def exact_implication(
    base: BaseClass,
    conditions: list[NegativeCondition],
    rule: RuleKey,
    rule_residues: set[int],
    max_ratio: int,
) -> ImplicationResult:
    L = lcm_many(base.modulus, rule.q, *(condition.q for condition in conditions))
    ratio = L // base.modulus
    if ratio > max_ratio:
        return ImplicationResult(status="unknown_large_lcm", implied=False, minimal_conditions=tuple(conditions), ratio=ratio, reason="implication_refinement_ratio_exceeds_limit")

    allowed = 0
    for offset in range(ratio):
        residue = (base.normalized_residue + offset * base.modulus) % L
        if any(residue % condition.q in condition.excluded_set for condition in conditions):
            continue
        allowed += 1
        if residue % rule.q not in rule_residues:
            return ImplicationResult(
                status="failed_counterexample",
                implied=False,
                minimal_conditions=tuple(conditions),
                ratio=ratio,
                tested_residue_count=allowed,
                counterexample_residue=residue,
                reason="allowed_residue_not_in_rule_set",
            )
    if allowed == 0:
        return ImplicationResult(
            status="empty_assumptions",
            implied=True,
            minimal_conditions=tuple(conditions),
            ratio=ratio,
            tested_residue_count=0,
            reason="conditions_leave_no_visible_residue",
        )
    return ImplicationResult(
        status="implied",
        implied=True,
        minimal_conditions=tuple(conditions),
        ratio=ratio,
        tested_residue_count=allowed,
        reason="all_allowed_residues_hit_rule_set",
    )


def find_minimal_implication(
    remainder: Remainder,
    rule: RuleKey,
    rule_residues: set[int],
    max_ratio: int,
    max_subset_conditions: int,
) -> ImplicationResult:
    no_condition = exact_implication(remainder.base_class, [], rule, rule_residues, max_ratio)
    if no_condition.implied and no_condition.status != "empty_assumptions":
        return no_condition

    conditions = sorted(remainder.conditions, key=lambda condition: (condition.q, len(condition.excluded_set)))[:max_subset_conditions]
    best_unknown: ImplicationResult | None = no_condition if no_condition.status == "unknown_large_lcm" else None

    for condition in conditions:
        result = exact_implication(remainder.base_class, [condition], rule, rule_residues, max_ratio)
        if result.implied:
            return result
        if result.status == "unknown_large_lcm" and best_unknown is None:
            best_unknown = result

    for index, first in enumerate(conditions):
        for second in conditions[index + 1 :]:
            result = exact_implication(remainder.base_class, [first, second], rule, rule_residues, max_ratio)
            if result.implied:
                return result
            if result.status == "unknown_large_lcm" and best_unknown is None:
                best_unknown = result

    return best_unknown or no_condition


def simplify_remainder(
    remainder: Remainder,
    max_pair_ratio: int,
    max_pair_checks: int,
    small_pair_threshold: int,
    max_enumerated_pair_residues: int,
    relation_counter: Counter[tuple[str, int, int, int]],
    relation_examples: dict[tuple[str, int, int, int], str],
) -> tuple[list[NegativeCondition], int, bool, str, str]:
    conditions_by_q: defaultdict[int, set[int]] = defaultdict(set)
    source_by_q: dict[int, RuleKey | None] = {}
    for condition in remainder.conditions:
        conditions_by_q[condition.q].update(condition.excluded_set)
        source_by_q.setdefault(condition.q, condition.source_rule)

    merged = [
        NegativeCondition(q=q, excluded_set=frozenset(values), source_rule=source_by_q.get(q))
        for q, values in sorted(conditions_by_q.items())
    ]
    removed = len(remainder.conditions) - len(merged)
    empty = False
    reason_parts: list[str] = []
    redundant_indices: set[int] = set()

    checks = 0
    for index, first in enumerate(merged):
        if index in redundant_indices:
            continue
        for jndex in range(index + 1, len(merged)):
            if jndex in redundant_indices:
                continue
            second = merged[jndex]
            if checks >= max_pair_checks:
                reason_parts.append("pair_check_limit_reached")
                break
            checks += 1
            relation = relation_for_pair(
                remainder.base_class,
                first,
                second,
                max_pair_ratio,
                small_pair_threshold,
                max_enumerated_pair_residues,
            )
            relation_key = (relation.status, remainder.base_class.focus_r, first.q, second.q)
            relation_counter[relation_key] += 1
            relation_examples.setdefault(relation_key, remainder.base_class.text)

            if relation.status == "contradiction":
                empty = True
                reason_parts.append(f"pair_contradiction_q_{first.q}_{second.q}")
                break
            if relation.status in ("a_implies_b", "equivalent"):
                redundant_indices.add(jndex)
            elif relation.status == "b_implies_a":
                redundant_indices.add(index)
                break
        if empty:
            break

    simplified = [condition for idx, condition in enumerate(merged) if idx not in redundant_indices]
    removed += len(redundant_indices)
    if remainder.visible_truncated:
        reason_parts.append("truncated_visible_conditions_only")
    if checks >= max_pair_checks:
        status = "unknown_large_lcm_or_pair_limit"
    elif empty:
        status = "empty"
    else:
        status = "simplified"
    return simplified, removed, empty, status, ";".join(reason_parts) or "visible_conditions_checked"


def condition_list_text(conditions: list[NegativeCondition], limit: int = 12) -> str:
    parts = [condition.text for condition in conditions[:limit]]
    if len(conditions) > limit:
        parts.append(f"... {len(conditions) - limit} more")
    return " AND ".join(parts)


def relation_summary_rows(
    relation_counter: Counter[tuple[str, int, int, int]],
    relation_examples: dict[tuple[str, int, int, int], str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    grouped_totals: Counter[tuple[int, int, int]] = Counter()
    for (_status, focus_r, q_a, q_b), count in relation_counter.items():
        grouped_totals[(focus_r, q_a, q_b)] += count
    for (status, focus_r, q_a, q_b), count in relation_counter.most_common():
        total = grouped_totals[(focus_r, q_a, q_b)]
        rows.append(
            {
                "relation_type": normalize_relation_type(status),
                "focus_r": focus_r,
                "qA": q_a,
                "qB": q_b,
                "count": count,
                "success_rate": count / total if total else 0,
                "example_base_class": relation_examples.get((status, focus_r, q_a, q_b), ""),
                "notes": status,
            }
        )
    return rows


def normalize_relation_type(status: str) -> str:
    if status == "a_implies_b":
        return "implies"
    if status == "b_implies_a":
        return "implies"
    if status == "equivalent":
        return "equivalent"
    if status == "contradiction":
        return "contradiction"
    if status == "symbolic_too_large":
        return "unknown_large_lcm"
    if status in ("a_implies_b", "b_implies_a"):
        return "redundant"
    return status


def analyze_implications(
    remainders: list[Remainder],
    candidates: list[tuple[RuleKey, set[int], int]],
    max_implication_ratio: int,
    max_rules_per_remainder: int,
    max_subset_conditions: int,
    max_implication_rows_per_focus: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    implication_rows: list[dict[str, object]] = []
    lemma_rows: list[dict[str, object]] = []
    lemma_id = 1

    grouped: defaultdict[int, list[Remainder]] = defaultdict(list)
    for remainder in remainders:
        grouped[remainder.base_class.focus_r].append(remainder)

    for focus_r in FOCUS_RESIDUES:
        rows_for_focus = 0
        for remainder in grouped.get(focus_r, []):
            rules_to_try = candidates[:max_rules_per_remainder]
            for rule, residues, _score in rules_to_try:
                if rows_for_focus >= max_implication_rows_per_focus:
                    break
                result = find_minimal_implication(
                    remainder,
                    rule,
                    residues,
                    max_implication_ratio,
                    max_subset_conditions,
                )
                implication_rows.append(
                    {
                        "focus_r": remainder.base_class.focus_r,
                        "base_modulus": remainder.base_class.modulus,
                        "base_residue": remainder.base_class.normalized_residue,
                        "rule_d": rule.d,
                        "rule_a": rule.a,
                        "rule_b": rule.b,
                        "rule_q": rule.q,
                        "implied": result.implied,
                        "minimal_conditions_used": condition_list_text(list(result.minimal_conditions), limit=4),
                        "refinement_ratio": result.ratio if result.ratio is not None else "",
                        "status": result.status,
                        "counterexample_residue_if_failed": result.counterexample_residue if result.counterexample_residue is not None else "",
                    }
                )
                rows_for_focus += 1
                if result.implied and result.status == "implied":
                    L = lcm_many(remainder.base_class.modulus, rule.q, *(condition.q for condition in result.minimal_conditions))
                    lemma_rows.append(
                        {
                            "lemma_id": lemma_id,
                            "focus_r": remainder.base_class.focus_r,
                            "base_modulus": remainder.base_class.modulus,
                            "base_residue": remainder.base_class.normalized_residue,
                            "conditions_used": condition_list_text(list(result.minimal_conditions), limit=8),
                            "rule_d": rule.d,
                            "rule_a": rule.a,
                            "rule_b": rule.b,
                            "rule_q": rule.q,
                            "verified_modulus": L,
                            "tested_residue_count": result.tested_residue_count or 0,
                            "status": "algebraically_verified_for_visible_conditions",
                        }
                    )
                    lemma_id += 1
            if rows_for_focus >= max_implication_rows_per_focus:
                break
    return implication_rows, lemma_rows


def write_candidate_lemmas(lemma_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Negative Condition Candidate Lemmas",
        "",
        "These lemmas are local residue-class implications over visible negative",
        "conditions only. They are not a proof of the Erdos-Straus conjecture.",
        "",
    ]
    if not lemma_rows:
        lines.extend(
            [
                "No strong negative-condition lemma found.",
                "",
                "All implication attempts were either failed on a bounded residue",
                "check or exceeded the configured refinement-ratio limit.",
            ]
        )
    for row in lemma_rows[:30]:
        lines.extend(
            [
                f"## Lemma candidate {row['lemma_id']}",
                "",
                "Base condition:",
                f"  n == {row['base_residue']} mod {row['base_modulus']}",
                "",
                "Negative assumptions:",
                f"  {row['conditions_used'] or '(none)'}",
                "",
                "Conclusion:",
                f"  rule (d={row['rule_d']}, a={row['rule_a']}, b={row['rule_b']}) applies.",
                "",
                "Meaning:",
                f"  x = (n+{row['rule_d']})/4",
                f"  y = n(n+{row['rule_d']})/{row['rule_a']}",
                f"  z = n(n+{row['rule_d']})/{row['rule_b']}",
                "",
                "Verification:",
                f"  checked all residues modulo L = {row['verified_modulus']}",
                f"  tested residue count = {row['tested_residue_count']}",
                f"  status: {row['status']}",
                "",
            ]
        )
    lines.append("Important: no full-conjecture proof is claimed here.")
    Path("negative_condition_candidate_lemmas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_focus_reports(
    remainders: list[Remainder],
    simplified_rows: list[dict[str, object]],
    relation_rows: list[dict[str, object]],
    implication_rows: list[dict[str, object]],
    lemma_rows: list[dict[str, object]],
) -> None:
    for focus_r in FOCUS_RESIDUES:
        focus_remainders = [remainder for remainder in remainders if remainder.base_class.focus_r == focus_r]
        focus_simplified = [row for row in simplified_rows if row["focus_r"] == focus_r]
        focus_relations = [row for row in relation_rows if int(row["focus_r"]) == focus_r]
        focus_implications = [row for row in implication_rows if int(row["focus_r"]) == focus_r]
        focus_lemmas = [row for row in lemma_rows if int(row["focus_r"]) == focus_r]
        q_counter: Counter[int] = Counter()
        for remainder in focus_remainders:
            q_counter.update(condition.q for condition in remainder.conditions)
        lines = [
            f"# Negative Condition Focus {focus_r} Report",
            "",
            "This is a local diagnostic report, not a proof.",
            "",
            f"Remainders analyzed: `{len(focus_remainders)}`.",
            f"Simplified rows: `{len(focus_simplified)}`.",
            f"Empty remainders found: `{sum(row['empty'] for row in focus_simplified)}`.",
            f"Redundant conditions removed: `{sum(int(row['removed_redundant']) for row in focus_simplified)}`.",
            f"Top visible q values: `{q_counter.most_common(10)}`.",
            "",
            "## Relations",
            "",
            f"Top relation rows: `{[(row['relation_type'], row['qA'], row['qB'], row['count']) for row in focus_relations[:10]]}`.",
            "",
            "## Rule Implications",
            "",
            f"Implication attempts recorded: `{len(focus_implications)}`.",
            f"Successful visible-condition implications: `{len(focus_lemmas)}`.",
            "",
            "## Best Candidate Lemmas",
            "",
        ]
        if focus_lemmas:
            for row in focus_lemmas[:5]:
                lines.append(
                    f"- lemma {row['lemma_id']}: base {row['base_residue']} mod "
                    f"{row['base_modulus']} => d={row['rule_d']}, pair=({row['rule_a']},{row['rule_b']})"
                )
        else:
            lines.append("No strong negative-condition lemma found for this focus.")
        unresolved = len(focus_remainders) - len(focus_lemmas)
        lines.extend(
            [
                "",
                f"Unresolved visible remainders after this diagnostic: `{max(unresolved, 0)}`.",
                "Verdict: not proved yet.",
            ]
        )
        Path(f"negative_condition_focus_{focus_r}_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_global_report(
    total: int,
    sampled: bool,
    simplified_rows: list[dict[str, object]],
    relation_rows: list[dict[str, object]],
    implication_rows: list[dict[str, object]],
    lemma_rows: list[dict[str, object]],
) -> None:
    relation_counter = Counter(row["relation_type"] for row in relation_rows)
    implication_counter = Counter(row["status"] for row in implication_rows)
    lines = [
        "# Negative Condition Global Report",
        "",
        "Previous simple lemmas of the form `n == c mod p` failed because the",
        "remaining core is constrained by many simultaneous negative residue-set",
        "conditions, not by one small congruence alone.",
        "",
        "This diagnostic studies relations between visible `not(...)` conditions.",
        "It uses bounded CRT/refinement checks and records unknown cases instead",
        "of expanding huge LCMs.",
        "",
        f"Remainders analyzed: `{total}`.",
        f"Analysis scope: `{'sampled analysis only' if sampled else 'full visible-condition analysis'}`.",
        f"Empty remainders found: `{sum(row['empty'] for row in simplified_rows)}`.",
        f"Redundant conditions removed: `{sum(int(row['removed_redundant']) for row in simplified_rows)}`.",
        f"Relation types: `{relation_counter.most_common()}`.",
        f"Implication statuses: `{implication_counter.most_common()}`.",
        f"Candidate lemmas verified: `{len(lemma_rows)}`.",
        "",
        "## Signs of Convergence",
        "",
        "Strong convergence would mean many contradictions, many redundant",
        "conditions, or many remainder-to-rule implications. In this run, the",
        "dominant obstruction is still bounded checks becoming too large or",
        "small-condition implications failing.",
        "",
        "## Next Mathematical Direction",
        "",
        "The most promising next direction is to prove general dominance rules",
        "between families of q-residue exclusions, especially when q values share",
        "large prime factors. That would avoid taking the full LCM of all visible",
        "conditions.",
        "",
        "Verdict: not proved yet.",
    ]
    if not lemma_rows:
        lines.append("")
        lines.append("No strong negative-condition lemma found.")
    Path("negative_condition_global_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze visible negative-condition relations.")
    parser.add_argument("--sample-limit", type=int, default=0, help="Limit remainders analyzed, spread evenly across focus residues. 0 means full.")
    parser.add_argument("--max-pair-refinement-ratio", type=int, default=200_000)
    parser.add_argument("--max-implication-refinement-ratio", type=int, default=200_000)
    parser.add_argument("--max-pair-checks-per-remainder", type=int, default=40)
    parser.add_argument("--max-enumerated-pair-residues", type=int, default=2_000)
    parser.add_argument("--small-pair-threshold", type=int, default=4)
    parser.add_argument("--max-candidate-rules", type=int, default=80)
    parser.add_argument("--max-rules-per-remainder", type=int, default=8)
    parser.add_argument("--max-subset-conditions", type=int, default=10)
    parser.add_argument("--max-implication-rows-per-focus", type=int, default=20_000)
    parser.add_argument("--max-rule-q", type=int, default=1_000_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_assert_tests()

    missing_optional = [path for path in OPTIONAL_INPUTS if not path.exists()]
    for path in missing_optional:
        print(f"warning: optional input missing: {path}")

    rule_sets, rule_by_signature = load_rule_residue_sets()
    remainders, missing_required, sampled = load_remainders(args.sample_limit, rule_by_signature)
    if missing_required:
        for path in missing_required:
            print(f"warning: required remainder file missing: {path}")
        if not remainders:
            raise SystemExit("no remainders available to analyze")

    relation_counter: Counter[tuple[str, int, int, int]] = Counter()
    relation_examples: dict[tuple[str, int, int, int], str] = {}
    simplified_rows: list[dict[str, object]] = []

    for remainder in remainders:
        simplified, removed, empty, status, reason = simplify_remainder(
            remainder,
            args.max_pair_refinement_ratio,
            args.max_pair_checks_per_remainder,
            args.small_pair_threshold,
            args.max_enumerated_pair_residues,
            relation_counter,
            relation_examples,
        )
        simplified_rows.append(
            {
                "focus_r": remainder.base_class.focus_r,
                "base_modulus": remainder.base_class.modulus,
                "base_residue": remainder.base_class.normalized_residue,
                "original_conditions": remainder.original_conditions_count,
                "simplified_conditions": len(simplified),
                "removed_redundant": removed,
                "empty": empty,
                "status": status,
                "reason": reason,
            }
        )

    write_csv(
        Path("negative_condition_simplified_remainders.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "original_conditions",
            "simplified_conditions",
            "removed_redundant",
            "empty",
            "status",
            "reason",
        ],
        simplified_rows,
    )

    relation_rows = relation_summary_rows(relation_counter, relation_examples)
    write_csv(
        Path("negative_condition_relation_summary.csv"),
        [
            "relation_type",
            "focus_r",
            "qA",
            "qB",
            "count",
            "success_rate",
            "example_base_class",
            "notes",
        ],
        relation_rows,
    )

    candidates = load_candidate_rules(rule_sets, args.max_candidate_rules, args.max_rule_q)
    implication_rows, lemma_rows = analyze_implications(
        remainders,
        candidates,
        args.max_implication_refinement_ratio,
        args.max_rules_per_remainder,
        args.max_subset_conditions,
        args.max_implication_rows_per_focus,
    )
    write_csv(
        Path("remainder_to_rule_implications.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "rule_d",
            "rule_a",
            "rule_b",
            "rule_q",
            "implied",
            "minimal_conditions_used",
            "refinement_ratio",
            "status",
            "counterexample_residue_if_failed",
        ],
        implication_rows,
    )
    write_csv(
        Path("minimal_negative_condition_lemmas.csv"),
        [
            "lemma_id",
            "focus_r",
            "base_modulus",
            "base_residue",
            "conditions_used",
            "rule_d",
            "rule_a",
            "rule_b",
            "rule_q",
            "verified_modulus",
            "tested_residue_count",
            "status",
        ],
        lemma_rows,
    )

    write_candidate_lemmas(lemma_rows)
    write_focus_reports(remainders, simplified_rows, relation_rows, implication_rows, lemma_rows)
    write_global_report(len(remainders), sampled, simplified_rows, relation_rows, implication_rows, lemma_rows)

    print(f"Total remainders analyzed: {len(remainders)}")
    if sampled:
        print("sampled analysis only")
    print(f"Simplified remainders: {len(simplified_rows)}")
    print(f"Empty remainders found: {sum(row['empty'] for row in simplified_rows)}")
    print(f"Redundant conditions removed: {sum(int(row['removed_redundant']) for row in simplified_rows)}")
    print(f"Top dominance relations: {[row for row in relation_rows if row['relation_type'] in ('implies', 'equivalent')][:5]}")
    print(f"Top contradiction relations: {[row for row in relation_rows if row['relation_type'] == 'contradiction'][:5]}")
    print(f"Remainder-to-rule implications found: {sum(1 for row in implication_rows if row['implied'])}")
    print(f"Candidate lemmas verified: {len(lemma_rows)}")
    print(f"Candidate lemmas failed: {sum(1 for row in implication_rows if row['status'] == 'failed_counterexample')}")
    print("Best next mathematical direction: prove family-level dominance between q-exclusion sets without full LCM expansion.")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
