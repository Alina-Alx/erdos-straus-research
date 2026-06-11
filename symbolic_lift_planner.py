#!/usr/bin/env python3
"""Plan symbolic lifts for unresolved recursive-cover leaves.

This is a research diagnostic. It replaces explicit lifted-subresidue
enumeration with fixed-rule residue sets modulo q = lcm(4, a, b) and CRT
intersection counts. It does not create a proof certificate.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Iterable


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
SQUARE_PRIMES = {289: 17, 361: 19, 529: 23, 841: 29, 961: 31}
DIAGNOSTICS_PATH = Path("recursive_failure_diagnostics.csv")
PREVIOUS_GROUPS_PATH = Path("recursive_failure_symbolic_groups.csv")
GROUPS_MD_PATH = Path("symbolic_lift_groups.md")
RULE_RESIDUE_PATH = Path("symbolic_rule_residue_sets.csv")
RULE_SUMMARY_PATH = Path("symbolic_rule_summary.csv")
INTERSECTION_PATH = Path("symbolic_class_rule_intersections.csv")
MASTER_KEYS_PATH = Path("symbolic_master_keys.csv")
SQUARE_RELATION_PATH = Path("square_core_prime_relation.csv")
LEMMAS_PATH = Path("candidate_lemmas.md")


@dataclass(frozen=True)
class SymbolicClass:
    modulus: int
    residue: int
    constraints: tuple[str, ...] = field(default_factory=tuple)

    @property
    def congruence(self) -> str:
        return f"n == {self.residue % self.modulus} mod {self.modulus}"


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def rule_modulus(self) -> int:
        return lcm_many(4, self.a, self.b)

    @property
    def pair_sum_ok(self) -> bool:
        return self.a + self.b == 4 * self.d


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


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


def factor_text(value: int) -> str:
    factors = factorization(value)
    if not factors:
        return "1"
    return "*".join(
        str(prime) if exponent == 1 else f"{prime}^{exponent}"
        for prime, exponent in factors
    )


def list_text(values: Iterable[int]) -> str:
    values = tuple(values)
    return ",".join(str(value) for value in values) if values else "none"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def required_paths() -> list[Path]:
    paths = [DIAGNOSTICS_PATH, PREVIOUS_GROUPS_PATH]
    paths.extend(Path(f"recursive_focus_{focus_r}_unresolved.csv") for focus_r in FOCUS_RESIDUES)
    return paths


def ensure_inputs() -> None:
    missing = [path for path in required_paths() if not path.exists()]
    if not missing:
        return
    missing_lines = "\n".join(f"  - {path}" for path in missing)
    raise SystemExit(f"missing required symbolic planner inputs:\n{missing_lines}")


def unresolved_counts() -> dict[int, int]:
    counts: dict[int, int] = {}
    for focus_r in FOCUS_RESIDUES:
        path = Path(f"recursive_focus_{focus_r}_unresolved.csv")
        with path.open(newline="", encoding="utf-8") as file:
            counts[focus_r] = sum(1 for _ in csv.DictReader(file))
    return counts


def int_or_none(value: str) -> int | None:
    return int(value) if value not in ("", None) else None


def lift_ratio(modulus: int, needed_lift: int | None) -> int | None:
    if needed_lift is None or needed_lift % modulus != 0:
        return None
    return needed_lift // modulus


def enriched_rows(raw_rows: list[dict[str, str]], max_leaves: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        if max_leaves and len(rows) >= max_leaves:
            break
        modulus = int(raw["modulus"])
        needed_lift = int_or_none(raw["needed_lift"])
        d = int_or_none(raw["d"])
        a = int_or_none(raw["a"])
        b = int_or_none(raw["b"])
        ratio = lift_ratio(modulus, needed_lift)
        row: dict[str, object] = {
            "focus_r": int(raw["focus_r"]),
            "depth": int(raw["depth"]),
            "modulus": modulus,
            "residue": int(raw["residue"]),
            "sample_n": int(raw["sample_n"]),
            "d": d,
            "a": a,
            "b": b,
            "rule_modulus": int_or_none(raw["rule_modulus"]),
            "needed_lift": needed_lift,
            "reason": raw["reason"],
            "lift_ratio": ratio,
            "missing_prime_factors": prime_factors(ratio or 1),
            "pair_sum": None if a is None or b is None else a + b,
            "check_pair_sum": (
                False if d is None or a is None or b is None else a + b == 4 * d
            ),
        }
        rows.append(row)
    return rows


def row_rule(row: dict[str, object]) -> Rule | None:
    d = row["d"]
    a = row["a"]
    b = row["b"]
    if d is None or a is None or b is None:
        return None
    return Rule(int(d), int(a), int(b))


def symbolic_groups(rows: list[dict[str, object]]) -> Counter[tuple[object, ...]]:
    groups: Counter[tuple[object, ...]] = Counter()
    for row in rows:
        rule = row_rule(row)
        ratio = row["lift_ratio"]
        if rule is None or ratio is None:
            continue
        groups[
            (
                int(row["focus_r"]),
                int(ratio),
                tuple(row["missing_prime_factors"]),
                rule.d,
                rule.a,
                rule.b,
                rule.rule_modulus,
            )
        ] += 1
    return groups


def group_sentence(key: tuple[object, ...], count: int) -> str:
    focus_r, ratio, primes, d, a, b, rule_modulus = key
    return (
        f"{count} unresolved leaves for focus r={focus_r} share "
        f"lift_ratio={ratio}, missing_prime_factors={list_text(primes)}, "
        f"d={d}, pair=({a},{b}), rule_modulus={rule_modulus}. "
        "This is a candidate symbolic pattern: a split by the listed factor "
        "may replace repeated explicit lifted subclasses."
    )


def write_groups_markdown(
    groups: Counter[tuple[object, ...]],
    rows_count: int,
    previous_group_count: int,
    sampled: bool,
    limit: int,
) -> None:
    lines = [
        "# Symbolic Lift Groups",
        "",
        "These are candidate symbolic patterns from unresolved recursive-cover leaves.",
        "They are not a proof of the Erdos-Straus conjecture.",
        "",
        f"Leaf rows analyzed: `{rows_count}`.",
        f"Previous group rows read: `{previous_group_count}`.",
        f"Analysis scope: `{'sampled analysis only' if sampled else 'all diagnostic leaves'}`.",
        "",
        f"## Top {limit} Groups",
        "",
    ]
    for index, (key, count) in enumerate(groups.most_common(limit), start=1):
        lines.append(f"{index}. {group_sentence(key, count)}")
    GROUPS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def frequent_rules(rows: list[dict[str, object]], limit: int) -> list[tuple[Rule, int]]:
    counts: Counter[Rule] = Counter()
    for row in rows:
        rule = row_rule(row)
        if rule is not None and rule.pair_sum_ok:
            counts[rule] += 1
    return counts.most_common(limit)


def rule_covers_residue(rule: Rule, residue: int) -> bool:
    if not rule.pair_sum_ok:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def rule_residue_sets(
    rules: list[tuple[Rule, int]],
    max_rule_modulus: int,
) -> dict[Rule, tuple[int, ...]]:
    residue_sets: dict[Rule, tuple[int, ...]] = {}
    with RULE_RESIDUE_PATH.open("w", newline="", encoding="utf-8") as residue_file:
        residue_writer = csv.DictWriter(
            residue_file,
            fieldnames=["d", "a", "b", "rule_modulus", "q", "residue_t"],
        )
        residue_writer.writeheader()
        with RULE_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as summary_file:
            summary_writer = csv.DictWriter(
                summary_file,
                fieldnames=[
                    "d",
                    "a",
                    "b",
                    "rule_modulus",
                    "covered_residue_count",
                    "total_q",
                    "coverage_ratio",
                    "diagnostic_leaf_count",
                ],
            )
            summary_writer.writeheader()
            for rule, diagnostic_count in rules:
                q = rule.rule_modulus
                if q > max_rule_modulus:
                    covered: tuple[int, ...] = ()
                else:
                    covered = tuple(t for t in range(q) if rule_covers_residue(rule, t))
                    for t in covered:
                        residue_writer.writerow(
                            {
                                "d": rule.d,
                                "a": rule.a,
                                "b": rule.b,
                                "rule_modulus": q,
                                "q": q,
                                "residue_t": t,
                            }
                        )
                residue_sets[rule] = covered
                summary_writer.writerow(
                    {
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                        "rule_modulus": q,
                        "covered_residue_count": len(covered),
                        "total_q": q,
                        "coverage_ratio": f"{len(covered) / q:.12g}",
                        "diagnostic_leaf_count": diagnostic_count,
                    }
                )
    return residue_sets


def crt_intersection(m1: int, r1: int, m2: int, r2: int) -> tuple[int, int] | None:
    """Return the combined congruence or None if two congruences conflict."""
    if m1 <= 0 or m2 <= 0:
        raise ValueError("CRT moduli must be positive")
    r1 %= m1
    r2 %= m2
    gcd = math.gcd(m1, m2)
    difference = r2 - r1
    if difference % gcd != 0:
        return None

    m1_reduced = m1 // gcd
    m2_reduced = m2 // gcd
    if m2_reduced == 1:
        multiplier = 0
    else:
        multiplier = (
            (difference // gcd) * pow(m1_reduced, -1, m2_reduced)
        ) % m2_reduced
    modulus = m1 * m2_reduced
    residue = (r1 + m1 * multiplier) % modulus
    return modulus, residue


def write_intersections(
    rows: list[dict[str, object]],
    rules: list[tuple[Rule, int]],
    residue_sets: dict[Rule, tuple[int, ...]],
) -> None:
    fieldnames = [
        "focus_r",
        "modulus",
        "residue",
        "d",
        "a",
        "b",
        "rule_modulus",
        "lift_ratio",
        "intersection_count",
        "possible_rule_residue_count",
        "covered_fraction_estimate",
        "fully_covers",
        "partially_covers",
        "missing_prime_factors",
    ]
    with INTERSECTION_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            symbolic_class = SymbolicClass(
                modulus=int(row["modulus"]),
                residue=int(row["residue"]),
                constraints=(f"focus_r={row['focus_r']}",),
            )
            for rule, _ in rules:
                q = rule.rule_modulus
                symbolic_ratio = lcm_many(symbolic_class.modulus, q) // symbolic_class.modulus
                covered_residues = residue_sets.get(rule, ())
                intersection_count = sum(
                    1
                    for t in covered_residues
                    if crt_intersection(symbolic_class.modulus, symbolic_class.residue, q, t)
                    is not None
                )
                possible_count = q // math.gcd(symbolic_class.modulus, q)
                fully_covers = possible_count > 0 and intersection_count == possible_count
                partially_covers = 0 < intersection_count < possible_count
                writer.writerow(
                    {
                        "focus_r": row["focus_r"],
                        "modulus": symbolic_class.modulus,
                        "residue": symbolic_class.residue,
                        "d": rule.d,
                        "a": rule.a,
                        "b": rule.b,
                        "rule_modulus": q,
                        "lift_ratio": symbolic_ratio,
                        "intersection_count": intersection_count,
                        "possible_rule_residue_count": possible_count,
                        "covered_fraction_estimate": (
                            "0" if possible_count == 0 else f"{intersection_count / possible_count:.12g}"
                        ),
                        "fully_covers": fully_covers,
                        "partially_covers": partially_covers,
                        "missing_prime_factors": list_text(prime_factors(symbolic_ratio)),
                    }
                )


def write_master_keys(rows: list[dict[str, object]]) -> Counter[tuple[int, int, int, int, int]]:
    counts: Counter[tuple[int, int, int, int, int]] = Counter()
    ratios: defaultdict[tuple[int, int, int, int, int], list[int]] = defaultdict(list)
    examples: defaultdict[tuple[int, int, int, int, int], list[int]] = defaultdict(list)

    for row in rows:
        rule = row_rule(row)
        ratio = row["lift_ratio"]
        if rule is None or ratio is None:
            continue
        primes = tuple(row["missing_prime_factors"]) or (1,)
        for prime in primes:
            key = (int(row["focus_r"]), rule.d, rule.a, rule.b, int(prime))
            counts[key] += 1
            ratios[key].append(int(ratio))
            if len(examples[key]) < 5:
                examples[key].append(int(row["residue"]))

    with MASTER_KEYS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "focus_r",
                "d",
                "a",
                "b",
                "missing_prime",
                "count",
                "avg_lift_ratio",
                "example_residues",
            ],
        )
        writer.writeheader()
        for key, count in counts.most_common():
            focus_r, d, a, b, prime = key
            writer.writerow(
                {
                    "focus_r": focus_r,
                    "d": d,
                    "a": a,
                    "b": b,
                    "missing_prime": prime,
                    "count": count,
                    "avg_lift_ratio": f"{mean(ratios[key]):.12g}",
                    "example_residues": ";".join(str(value) for value in examples[key]),
                }
            )
    return counts


def missing_prime_counts(rows: list[dict[str, object]]) -> dict[int, Counter[int]]:
    counts: dict[int, Counter[int]] = defaultdict(Counter)
    for row in rows:
        focus_r = int(row["focus_r"])
        for prime in tuple(row["missing_prime_factors"]):
            counts[focus_r][int(prime)] += 1
    return counts


def write_square_relation(rows: list[dict[str, object]]) -> str:
    counts = missing_prime_counts(rows)
    square_ranks: list[int | None] = []
    with SQUARE_RELATION_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["focus_r", "square_prime", "missing_prime", "count", "rank"],
        )
        writer.writeheader()
        for focus_r in FOCUS_RESIDUES:
            ranked = counts[focus_r].most_common()
            rank_by_prime = {prime: index for index, (prime, _) in enumerate(ranked, start=1)}
            square_prime = SQUARE_PRIMES[focus_r]
            square_ranks.append(rank_by_prime.get(square_prime))
            for rank, (prime, count) in enumerate(ranked, start=1):
                writer.writerow(
                    {
                        "focus_r": focus_r,
                        "square_prime": square_prime,
                        "missing_prime": prime,
                        "count": count,
                        "rank": rank,
                    }
                )
            if square_prime not in rank_by_prime:
                writer.writerow(
                    {
                        "focus_r": focus_r,
                        "square_prime": square_prime,
                        "missing_prime": square_prime,
                        "count": 0,
                        "rank": "",
                    }
                )

    if all(rank == 1 for rank in square_ranks):
        return "pattern confirmed"
    close_ranks = [rank for rank in square_ranks if rank is not None and rank <= 10]
    if len(close_ranks) >= 3:
        return "pattern partially confirmed"
    return "pattern not confirmed"


def write_candidate_lemmas() -> None:
    lines = [
        "# Candidate Lemmas",
        "",
        "These notes do not prove the Erdos-Straus conjecture.",
        "They separate algebraic facts from computationally supported patterns.",
        "",
        "## Lemma Candidate A",
        "",
        "Status: computationally supported.",
        "",
        "For hard classes `n == p^2 mod 120120`, unresolved leaves often",
        "require lifts by primes `q` appearing in the fixed-rule pair `(a,b)`.",
        "A symbolic split by `q` may cover large repeated families.",
        "",
        "## Lemma Candidate B",
        "",
        "Status: proven algebraically.",
        "",
        "For a fixed general-key rule `(d,a,b)`, applicability depends only on",
        "`n mod q` for `q = lcm(4,a,b)`: the checks `(n+d) mod 4`,",
        "`n(n+d) mod a`, and `n(n+d) mod b` are congruence checks modulo",
        "divisors of `q`. Therefore the rule has a finite residue set modulo `q`.",
        "",
        "## Lemma Candidate C",
        "",
        "Status: conjectural as a cover strategy; algebraically valid as a",
        "representation of one rule split.",
        "",
        "If a class `C = (m,r)` is not covered by a sample rule `(d,a,b)` and",
        "the needed lift introduces a missing factor `q`, keep the symbolic",
        "condition `n mod lcm(4,a,b) in S_rule` and use CRT intersections",
        "instead of explicitly materializing all lifted subresidues.",
        "",
        "## Guardrail",
        "",
        "A symbolic planner can compress repeated congruence families, but a",
        "full cover still needs independently checked coverage of every class",
        "represented by the planner.",
    ]
    LEMMAS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_rule_coverage() -> list[dict[str, str]]:
    summaries = read_csv_rows(RULE_SUMMARY_PATH)
    summaries.sort(key=lambda row: float(row["coverage_ratio"]), reverse=True)
    print("\nrules with high symbolic coverage modulo their own q:")
    for row in summaries[:10]:
        print(
            f"  d={row['d']}, pair=({row['a']},{row['b']}), q={row['rule_modulus']}: "
            f"{row['covered_residue_count']}/{row['total_q']} = {row['coverage_ratio']}"
        )
    return summaries


def print_square_relation_summary() -> None:
    relation_rows = read_csv_rows(SQUARE_RELATION_PATH)
    ranks = {
        int(row["focus_r"]): int(row["rank"])
        for row in relation_rows
        if row["rank"] and int(row["missing_prime"]) == int(row["square_prime"])
    }
    print("\nsquare-core same-prime ranks:")
    for focus_r in FOCUS_RESIDUES:
        square_prime = SQUARE_PRIMES[focus_r]
        rank = ranks.get(focus_r)
        rank_text = "absent" if rank is None else str(rank)
        print(f"  r={focus_r}=({square_prime})^2: missing prime {square_prime} rank {rank_text}")


def print_report(
    rows: list[dict[str, object]],
    groups: Counter[tuple[object, ...]],
    master_counts: Counter[tuple[int, int, int, int, int]],
    square_verdict: str,
    sampled: bool,
    intersection_rule_count: int,
    unresolved_leaf_counts: dict[int, int],
) -> None:
    missing = Counter()
    d_counts = Counter()
    pair_counts = Counter()
    for row in rows:
        for prime in tuple(row["missing_prime_factors"]):
            missing[int(prime)] += 1
        rule = row_rule(row)
        if rule is not None:
            d_counts[rule.d] += 1
            pair_counts[(rule.a, rule.b)] += 1

    print("\nfinal symbolic planner report:")
    print(f"  unresolved leaves read: {len(rows)}")
    print(f"  unresolved source leaf counts: {unresolved_leaf_counts}")
    print(f"  analysis scope: {'sampled analysis only' if sampled else 'all diagnostic leaves'}")
    print(f"  top missing primes: {missing.most_common(10)}")
    print(f"  top d: {d_counts.most_common(10)}")
    print(f"  top pairs: {pair_counts.most_common(10)}")
    print("  top symbolic groups:")
    for key, count in groups.most_common(10):
        focus_r, ratio, primes, d, a, b, rule_modulus = key
        print(
            f"    r={focus_r} count={count} ratio={ratio} primes={list_text(primes)} "
            f"d={d} pair=({a},{b}) q={rule_modulus}"
        )
    print_rule_coverage()
    print(f"\n  CRT intersections written for top rules: {intersection_rule_count}")
    print(f"  top master keys: {master_counts.most_common(10)}")
    print_square_relation_summary()
    print(f"  square core relation: {square_verdict}")
    print(f"  candidate lemmas: {LEMMAS_PATH}")
    print("  recommended next step: build a symbolic cover engine over rule residue sets and CRT.")
    print("  alternative follow-up: test a square-core lemma only after symbolic splits are measured.")
    print("verdict: not proved yet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan symbolic lifts from recursive failures.")
    parser.add_argument("--max-leaves", type=int, default=0, help="0 means all diagnostic leaves.")
    parser.add_argument("--top-groups", type=int, default=50)
    parser.add_argument("--frequent-rule-limit", type=int, default=50)
    parser.add_argument("--intersection-rule-limit", type=int, default=10)
    parser.add_argument("--max-rule-modulus", type=int, default=2_000_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_inputs()
    source_unresolved_counts = unresolved_counts()

    raw_rows = read_csv_rows(DIAGNOSTICS_PATH)
    previous_groups = read_csv_rows(PREVIOUS_GROUPS_PATH)
    rows = enriched_rows(raw_rows, args.max_leaves)
    sampled = bool(args.max_leaves and args.max_leaves < len(raw_rows))

    bad_pair_rows = sum(
        1
        for row in rows
        if row_rule(row) is not None and not bool(row["check_pair_sum"])
    )
    if bad_pair_rows:
        print(f"warning: {bad_pair_rows} diagnostic rows fail a+b == 4d")

    groups = symbolic_groups(rows)
    write_groups_markdown(groups, len(rows), len(previous_groups), sampled, args.top_groups)

    frequent = frequent_rules(rows, args.frequent_rule_limit)
    residue_sets = rule_residue_sets(frequent, args.max_rule_modulus)
    intersection_rules = frequent[: args.intersection_rule_limit]
    write_intersections(rows, intersection_rules, residue_sets)
    master_counts = write_master_keys(rows)
    square_verdict = write_square_relation(rows)
    write_candidate_lemmas()
    print_report(
        rows,
        groups,
        master_counts,
        square_verdict,
        sampled,
        len(intersection_rules),
        source_unresolved_counts,
    )


if __name__ == "__main__":
    main()
