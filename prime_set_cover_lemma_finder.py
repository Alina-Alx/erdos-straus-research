#!/usr/bin/env python3
"""Group family rules by shared prime moduli and test small prime-set covers.

Earlier diagnostics showed an obstruction: direct implications

    NOT(rule_1) AND ... => target_rule

usually fail when the target rule introduces a fresh prime modulus.  This
script takes the next step and groups rules by the primes that appear in their
family conditions.  It then tests small fixed-prime universes where every
target prime is already present, so the "fresh prime" obstruction is removed.

The finite cover checks are intentionally modest.  They enumerate residues
modulo the lcm of the selected rule-condition moduli only when that modulus is
small enough.  This is a lemma-discovery tool, not a proof certificate.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATA_DIR = Path("data")
AUTOMATIC_RULES_PATH = DATA_DIR / "automatic_small_factor_rules.csv"
COMPOUND_RULES_PATH = DATA_DIR / "compound_factor_family_rules.csv"
MASTER_KEYS_PATH = DATA_DIR / "symbolic_master_keys.csv"


@dataclass(frozen=True)
class Condition:
    modulus: int
    residues: frozenset[int]


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int
    support_count: int
    source: str
    conditions: tuple[Condition, ...]

    @property
    def label(self) -> str:
        return f"d={self.d},a={self.a},b={self.b}"

    @property
    def condition_moduli(self) -> tuple[int, ...]:
        return tuple(condition.modulus for condition in self.conditions if condition.modulus != 24)

    @property
    def prime_signature(self) -> tuple[int, ...]:
        primes: set[int] = set()
        for modulus in self.condition_moduli:
            primes.update(factorization(modulus))
        return tuple(sorted(primes))


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


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def factorization(value: int) -> tuple[int, ...]:
    factors: list[int] = []
    n = value
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            factors.append(divisor)
            while n % divisor == 0:
                n //= divisor
        divisor += 1 if divisor == 2 else 2
    if n > 1:
        factors.append(n)
    return tuple(factors)


def parse_extra_moduli(text: str) -> list[int]:
    if not text:
        return []
    return [int(part) for part in text.split(";") if part]


def local_residue_set(d: int, modulus: int) -> frozenset[int]:
    return frozenset(
        residue
        for residue in range(modulus)
        if (residue * (residue + d)) % modulus == 0
    )


def build_auto_rule(row: dict[str, str]) -> Rule | None:
    if row.get("prime_condition_enough_on_n_1_mod_24") != "True":
        return None
    p = csv_int(row, "dominant_prime")
    if p <= 1:
        return None
    d = csv_int(row, "d")
    conditions = (
        Condition(24, frozenset({1})),
        Condition(p, frozenset({0, (-d) % p})),
    )
    return Rule(
        d=d,
        a=csv_int(row, "a"),
        b=csv_int(row, "b"),
        support_count=csv_int(row, "support_count", 1),
        source="automatic",
        conditions=conditions,
    )


def build_compound_rule(row: dict[str, str]) -> Rule | None:
    if row.get("compound_conditions_enough") != "True":
        return None
    p = csv_int(row, "dominant_prime")
    if p <= 1:
        return None
    d = csv_int(row, "d")
    conditions: list[Condition] = [
        Condition(24, frozenset({1})),
        Condition(p, frozenset({0, (-d) % p})),
    ]
    for modulus in parse_extra_moduli(row.get("extra_moduli", "")):
        conditions.append(Condition(modulus, local_residue_set(d, modulus)))
    return Rule(
        d=d,
        a=csv_int(row, "a"),
        b=csv_int(row, "b"),
        support_count=csv_int(row, "support_count", 1),
        source="compound",
        conditions=tuple(conditions),
    )


def load_rules(limit: int) -> list[Rule]:
    rules_by_key: dict[tuple[int, int, int], Rule] = {}
    if AUTOMATIC_RULES_PATH.exists():
        for row in read_csv_rows(AUTOMATIC_RULES_PATH):
            rule = build_auto_rule(row)
            if rule is not None:
                rules_by_key[(rule.d, rule.a, rule.b)] = rule
    if COMPOUND_RULES_PATH.exists():
        for row in read_csv_rows(COMPOUND_RULES_PATH):
            rule = build_compound_rule(row)
            if rule is not None:
                rules_by_key[(rule.d, rule.a, rule.b)] = rule
    return sorted(rules_by_key.values(), key=lambda rule: rule.support_count, reverse=True)[:limit]


def load_master_prime_weights() -> Counter[int]:
    weights: Counter[int] = Counter()
    if not MASTER_KEYS_PATH.exists():
        return weights
    for row in read_csv_rows(MASTER_KEYS_PATH):
        prime = csv_int(row, "missing_prime")
        weights[prime] += csv_int(row, "count", 1)
    return weights


def rule_holds_mod(rule: Rule, residue: int) -> bool:
    return all(residue % condition.modulus in condition.residues for condition in rule.conditions)


def cover_stats_for_rules(rules: list[Rule], max_modulus: int) -> dict[str, object]:
    modulus = 24
    for rule in rules:
        for condition in rule.conditions:
            modulus = lcm_many(modulus, condition.modulus)
            if modulus > max_modulus:
                return {
                    "status": "too_large",
                    "modulus": modulus,
                    "target_residues": "",
                    "covered_residues": "",
                    "coverage_ratio": "",
                    "uncovered_examples": "",
                }

    target = [residue for residue in range(modulus) if residue % 24 == 1]
    covered = [
        residue
        for residue in target
        if any(rule_holds_mod(rule, residue) for rule in rules)
    ]
    uncovered = [residue for residue in target if residue not in set(covered)]
    ratio = len(covered) / len(target) if target else 0.0
    return {
        "status": "checked",
        "modulus": modulus,
        "target_residues": len(target),
        "covered_residues": len(covered),
        "coverage_ratio": f"{ratio:.6f}",
        "uncovered_examples": ";".join(str(x) for x in uncovered[:20]),
    }


def rule_group_rows(rules: list[Rule]) -> list[dict[str, object]]:
    by_signature: defaultdict[tuple[int, ...], list[Rule]] = defaultdict(list)
    by_prime: defaultdict[int, list[Rule]] = defaultdict(list)
    for rule in rules:
        by_signature[rule.prime_signature].append(rule)
        for prime in rule.prime_signature:
            by_prime[prime].append(rule)

    rows: list[dict[str, object]] = []
    for signature, group in sorted(
        by_signature.items(),
        key=lambda item: sum(rule.support_count for rule in item[1]),
        reverse=True,
    ):
        rows.append(
            {
                "group_type": "exact_signature",
                "prime_set": ";".join(str(p) for p in signature),
                "rule_count": len(group),
                "support_count": sum(rule.support_count for rule in group),
                "rules": " | ".join(rule.label for rule in group[:12]),
            }
        )
    for prime, group in sorted(
        by_prime.items(),
        key=lambda item: sum(rule.support_count for rule in item[1]),
        reverse=True,
    ):
        rows.append(
            {
                "group_type": "contains_prime",
                "prime_set": str(prime),
                "rule_count": len(group),
                "support_count": sum(rule.support_count for rule in group),
                "rules": " | ".join(rule.label for rule in group[:12]),
            }
        )
    return rows


def candidate_prime_sets(rules: list[Rule], max_prime_set_size: int) -> list[tuple[int, ...]]:
    support_by_prime: Counter[int] = Counter()
    for rule in rules:
        for prime in rule.prime_signature:
            support_by_prime[prime] += rule.support_count
    top_primes = [prime for prime, _support in support_by_prime.most_common(12)]

    candidates: set[tuple[int, ...]] = set()
    for size in range(1, max_prime_set_size + 1):
        for combo in itertools.combinations(top_primes, size):
            candidates.add(tuple(sorted(combo)))

    # Also include exact signatures from high-support rules.
    for rule in rules[:80]:
        if len(rule.prime_signature) <= max_prime_set_size:
            candidates.add(rule.prime_signature)
    return sorted(candidates, key=lambda item: (len(item), item))


def evaluate_prime_sets(
    rules: list[Rule],
    max_prime_set_size: int,
    max_modulus: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for prime_set in candidate_prime_sets(rules, max_prime_set_size):
        selected = [
            rule
            for rule in rules
            if set(rule.prime_signature).issubset(prime_set)
        ]
        if not selected:
            continue
        stats = cover_stats_for_rules(selected, max_modulus)
        rows.append(
            {
                "prime_set": ";".join(str(p) for p in prime_set),
                "prime_set_size": len(prime_set),
                "rule_count": len(selected),
                "support_count": sum(rule.support_count for rule in selected),
                "status": stats["status"],
                "modulus": stats["modulus"],
                "target_residues": stats["target_residues"],
                "covered_residues": stats["covered_residues"],
                "coverage_ratio": stats["coverage_ratio"],
                "uncovered_examples": stats["uncovered_examples"],
                "rules": " | ".join(rule.label for rule in selected[:15]),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["status"] != "checked",
            -float(row["coverage_ratio"] or 0),
            -int(row["support_count"]),
        ),
    )


def write_report(
    rules: list[Rule],
    group_rows: list[dict[str, object]],
    cover_rows: list[dict[str, object]],
) -> None:
    prime_support = Counter()
    for rule in rules:
        for prime in rule.prime_signature:
            prime_support[prime] += rule.support_count
    master_weights = load_master_prime_weights()
    checked_rows = [row for row in cover_rows if row["status"] == "checked"]
    best_checked = checked_rows[:10]

    lines = [
        "# Prime-Set Cover Lemma Report",
        "",
        "This report groups family rules by shared prime moduli and tests small",
        "fixed-prime universes. The goal is to avoid the previous obstruction",
        "where a target rule introduced a fresh independent prime.",
        "",
        "This is a finite diagnostic over selected rule families, not a proof",
        "of the full Erdős-Straus conjecture.",
        "",
        "## Prime Support",
        "",
        f"- top condition primes by rule support: `{prime_support.most_common(15)}`",
        f"- top missing primes from symbolic master keys: `{master_weights.most_common(15)}`",
        "",
        "## Strongest Rule Groups",
        "",
    ]
    for row in group_rows[:20]:
        lines.extend(
            [
                f"### {row['group_type']} `{row['prime_set']}`",
                "",
                f"- rule count: `{row['rule_count']}`",
                f"- support count: `{row['support_count']}`",
                f"- examples: `{row['rules']}`",
                "",
            ]
        )

    lines.extend(["## Best Small Fixed-Prime Cover Checks", ""])
    if not best_checked:
        lines.append("No finite cover check was small enough under the current modulus cap.")
        lines.append("")
    else:
        for row in best_checked:
            lines.extend(
                [
                    f"### primes `{row['prime_set']}`",
                    "",
                    f"- status: `{row['status']}`",
                    f"- modulus: `{row['modulus']}`",
                    f"- rules: `{row['rule_count']}`",
                    f"- covered residues: `{row['covered_residues']}/{row['target_residues']}`",
                    f"- coverage ratio: `{row['coverage_ratio']}`",
                    f"- uncovered examples: `{row['uncovered_examples']}`",
                    f"- rule examples: `{row['rules']}`",
                    "",
                ]
            )

    lines.extend(
        [
            "## Lemma Direction",
            "",
            "A promising family lemma should fix a small prime universe `P` and",
            "only use rules whose condition primes are contained in `P`. Inside",
            "that universe, target primes are not fresh; the obstruction from",
            "`family_negative_obstruction_report.md` no longer applies.",
            "",
            "A successful cover statement would have the form:",
            "",
            "```text",
            "For n == 1 mod 24 and residues modulo M(P), at least one rule",
            "with prime_signature(rule) subset P applies.",
            "```",
            "",
            "The current finite checks are partial diagnostics. They do not prove",
            "the conjecture.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("reports/prime_set_cover_lemma_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rules", type=int, default=250)
    parser.add_argument("--max-prime-set-size", type=int, default=3)
    parser.add_argument("--max-modulus", type=int, default=2_000_000)
    args = parser.parse_args()

    rules = load_rules(args.max_rules)
    group_rows = rule_group_rows(rules)
    cover_rows = evaluate_prime_sets(
        rules,
        max_prime_set_size=args.max_prime_set_size,
        max_modulus=args.max_modulus,
    )

    write_csv(
        Path("data/prime_set_rule_groups.csv"),
        ["group_type", "prime_set", "rule_count", "support_count", "rules"],
        group_rows,
    )
    write_csv(
        Path("data/prime_set_cover_checks.csv"),
        [
            "prime_set",
            "prime_set_size",
            "rule_count",
            "support_count",
            "status",
            "modulus",
            "target_residues",
            "covered_residues",
            "coverage_ratio",
            "uncovered_examples",
            "rules",
        ],
        cover_rows,
    )
    write_report(rules, group_rows, cover_rows)

    checked = [row for row in cover_rows if row["status"] == "checked"]
    print(f"Rules loaded: {len(rules)}")
    print(f"Prime groups written: {len(group_rows)}")
    print(f"Prime-set cover candidates: {len(cover_rows)}")
    print(f"Finite checked candidates: {len(checked)}")
    if checked:
        best = checked[0]
        print(
            "Best checked cover: "
            f"primes={best['prime_set']} ratio={best['coverage_ratio']} "
            f"covered={best['covered_residues']}/{best['target_residues']}"
        )
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
