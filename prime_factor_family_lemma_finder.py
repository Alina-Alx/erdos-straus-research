#!/usr/bin/env python3
"""Find prime-factor rule families for the general-key formulas.

This script looks for human-readable families in rules (d,a,b), especially
when q = lcm(4,a,b) is controlled by one large prime factor. It does not build
a cover engine and it does not claim a proof of the Erdos-Straus conjecture.
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INPUTS = [
    Path("remaining_sample_minimal_rules.csv"),
    Path("symbolic_rule_summary.csv"),
    Path("symbolic_master_keys.csv"),
    Path("symbolic_rule_residue_sets.csv"),
]


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)

    @property
    def l_ab(self) -> int:
        return lcm_many(self.a, self.b)

    @property
    def pair_sum_ok(self) -> bool:
        return self.a + self.b == 4 * self.d


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


def int_value(value: str | None, default: int = 0) -> int:
    return int(value) if value not in ("", None) else default


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


def factor_text(value: int) -> str:
    factors = factorization(value)
    if not factors:
        return str(value)
    return "*".join(
        str(prime) if exponent == 1 else f"{prime}^{exponent}"
        for prime, exponent in factors
    )


def is_prime(value: int) -> bool:
    return value > 1 and factorization(value) == ((value, 1),)


def prime_power(prime: int, exponent: int) -> int:
    return prime**exponent


def rule_works_on_residue(rule: Rule, residue: int) -> bool:
    if not rule.pair_sum_ok:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def direct_residue_set(rule: Rule) -> set[int]:
    return {residue for residue in range(rule.q) if rule_works_on_residue(rule, residue)}


def local_prime_power_sets(rule: Rule) -> list[tuple[int, int, int, set[int]]]:
    local: list[tuple[int, int, int, set[int]]] = []
    for prime, exponent in factorization(rule.l_ab):
        modulus = prime_power(prime, exponent)
        residues = {
            residue
            for residue in range(modulus)
            if (residue * (residue + rule.d)) % modulus == 0
        }
        local.append((prime, exponent, modulus, residues))
    return local


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


def combine_residue_conditions(conditions: list[tuple[int, set[int]]]) -> tuple[int, set[int]]:
    modulus = 1
    residues = {0}
    for next_modulus, next_residues in conditions:
        combined_modulus = lcm_many(modulus, next_modulus)
        combined: set[int] = set()
        for left in residues:
            for right in next_residues:
                intersection = crt_intersection(modulus, left, next_modulus, right)
                if intersection is not None:
                    _, residue = intersection
                    combined.add(residue % combined_modulus)
        modulus = combined_modulus
        residues = combined
    return modulus, residues


def prime_power_residue_set(rule: Rule) -> set[int]:
    conditions: list[tuple[int, set[int]]] = [(
        4,
        {(-rule.d) % 4},
    )]
    for _prime, _exponent, modulus, residues in local_prime_power_sets(rule):
        conditions.append((modulus, residues))
    modulus, residues = combine_residue_conditions(conditions)
    if modulus != rule.q:
        lifted = set()
        for residue in residues:
            for candidate in range(residue, rule.q, modulus):
                lifted.add(candidate)
        return lifted
    return residues


def dominant_prime(rule: Rule) -> int | None:
    factors = factorization(rule.l_ab)
    prime_candidates = [prime for prime, exponent in factors if exponent == 1 and prime > 3]
    if not prime_candidates:
        return None
    return max(prime_candidates)


def classify_template(rule: Rule) -> tuple[str, int | None]:
    a, b, d = rule.a, rule.b, rule.d
    p = None
    if a == 1 and is_prime(b) and b == 4 * d - 1:
        return "F1: a=1, b=p=4d-1", b
    if a == 2 and b % 2 == 0 and is_prime(b // 2) and b == 4 * d - 2:
        return "F2: a=2, b=2p, p=2d-1", b // 2
    if a == 3 and is_prime(b) and b == 4 * d - 3:
        return "F3: a=3, b=p=4d-3", b
    if a == 6 and b % 2 == 0 and is_prime(b // 2) and b == 4 * d - 6:
        return "F4: a=6, b=2p, p=2d-3", b // 2
    if a == 24 and b % 4 == 0 and is_prime(b // 4) and b == 4 * d - 24:
        return "F5: a=24, b=4p, p=d-6", b // 4
    p = dominant_prime(rule)
    if p:
        return "G: one dominant prime factor in lcm(a,b)", p
    return "other", None


def hard_core_residues_mod_p(rule: Rule, p: int) -> set[int]:
    if p <= 3 or math.gcd(p, 24) != 1:
        return set()
    residues: set[int] = set()
    for s in range(p):
        intersection = crt_intersection(24, 1, p, s)
        if intersection is None:
            continue
        modulus, residue = intersection
        works = all(rule_works_on_residue(rule, candidate % rule.q) for candidate in range(residue, lcm_many(modulus, rule.q), modulus))
        if works:
            residues.add(s)
    return residues


def load_rule_counts() -> Counter[Rule]:
    counts: Counter[Rule] = Counter()
    for path in INPUTS:
        if not path.exists() or path.name == "symbolic_rule_residue_sets.csv":
            continue
        for row in read_csv_rows(path):
            if not row.get("d") or not row.get("a") or not row.get("b"):
                continue
            rule = Rule(int(row["d"]), int(row["a"]), int(row["b"]))
            weight = (
                int_value(row.get("diagnostic_leaf_count"))
                or int_value(row.get("count"))
                or 1
            )
            counts[rule] += weight
    return counts


def load_known_residue_sets() -> dict[Rule, set[int]]:
    path = Path("symbolic_rule_residue_sets.csv")
    known: defaultdict[Rule, set[int]] = defaultdict(set)
    if not path.exists():
        return {}
    for row in read_csv_rows(path):
        rule = Rule(int(row["d"]), int(row["a"]), int(row["b"]))
        known[rule].add(int(row["residue_t"]) % rule.q)
    return dict(known)


def analyze_rules(counts: Counter[Rule], known_sets: dict[Rule, set[int]], limit: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    summary_rows: list[dict[str, object]] = []
    test_rows: list[dict[str, object]] = []
    for rule, support in counts.most_common(limit):
        template, p = classify_template(rule)
        direct = known_sets.get(rule) or direct_residue_set(rule)
        factor_set = prime_power_residue_set(rule)
        factor_test_passed = direct == factor_set
        hard_residues = hard_core_residues_mod_p(rule, p) if p else set()
        expected_simple = set()
        if p and math.gcd(rule.d, p) == 1:
            expected_simple = {0, (-rule.d) % p}
        hard_matches_simple = bool(hard_residues) and hard_residues == expected_simple
        local_text = "; ".join(
            f"{prime}^{exponent} mod {modulus}: {sorted(residues)[:8]}"
            + ("..." if len(residues) > 8 else "")
            for prime, exponent, modulus, residues in local_prime_power_sets(rule)
        )
        summary_rows.append(
            {
                "d": rule.d,
                "a": rule.a,
                "b": rule.b,
                "q": rule.q,
                "lcm_a_b": rule.l_ab,
                "lcm_a_b_factorization": factor_text(rule.l_ab),
                "support_count": support,
                "template": template,
                "dominant_prime": p or "",
                "residue_count": len(direct),
                "residue_set": ";".join(str(x) for x in sorted(direct)),
                "prime_power_local_conditions": local_text,
                "hard_core_residues_mod_p": "" if not p else ";".join(str(x) for x in sorted(hard_residues)),
                "hard_core_matches_{0,-d}_mod_p": hard_matches_simple,
            }
        )
        test_rows.append(
            {
                "d": rule.d,
                "a": rule.a,
                "b": rule.b,
                "q": rule.q,
                "template": template,
                "dominant_prime": p or "",
                "test_type": "prime_power_factorization_equals_direct_rule_set",
                "tested_modulus": rule.q,
                "passed": factor_test_passed,
                "status": "passed" if factor_test_passed else "failed",
                "details": f"direct={len(direct)} factor={len(factor_set)}",
            }
        )
        if p:
            hard_reduction_found = bool(hard_residues)
            test_rows.append(
                {
                    "d": rule.d,
                    "a": rule.a,
                    "b": rule.b,
                    "q": rule.q,
                    "template": template,
                    "dominant_prime": p,
                    "test_type": "hard_core_n_1_mod_24_reduces_to_mod_p",
                    "tested_modulus": lcm_many(24, rule.q),
                    "passed": hard_reduction_found,
                    "status": "reduction_found" if hard_reduction_found else "no_reduction_found",
                    "details": f"n mod p allowed={sorted(hard_residues)}",
                }
            )
    return summary_rows, test_rows


def write_markdown(summary_rows: list[dict[str, object]], test_rows: list[dict[str, object]]) -> None:
    template_counts = Counter(row["template"] for row in summary_rows)
    prime_power_passed = sum(
        1
        for row in test_rows
        if row["test_type"] == "prime_power_factorization_equals_direct_rule_set"
        and row["status"] == "passed"
    )
    prime_power_failed = sum(
        1
        for row in test_rows
        if row["test_type"] == "prime_power_factorization_equals_direct_rule_set"
        and row["status"] == "failed"
    )
    hard_reductions = sum(
        1
        for row in test_rows
        if row["test_type"] == "hard_core_n_1_mod_24_reduces_to_mod_p"
        and row["status"] == "reduction_found"
    )
    lines = [
        "# Prime-Factor Family Lemma Candidates",
        "",
        "This file looks for reusable rule families in `(d,a,b)` using prime",
        "factors of `q = lcm(4,a,b)`. It is not a proof of the full",
        "Erdos-Straus conjecture.",
        "",
        "## General Prime-Power Lemma",
        "",
        "For any fixed `d,a,b` with `a+b=4d`, let `L = lcm(a,b)`. If",
        "`n+d` is divisible by `4` and for every prime power `ell = p^e`",
        "dividing `L` we have `n(n+d) == 0 mod ell`, then",
        "",
        "`x=(n+d)/4`, `y=n(n+d)/a`, `z=n(n+d)/b`",
        "",
        "is a valid general-key solution. This is algebraic: the prime-power",
        "conditions imply `a | n(n+d)` and `b | n(n+d)`.",
        "",
        "## Frequent Families",
        "",
    ]
    for template, count in template_counts.most_common():
        lines.append(f"- `{template}`: {count} analyzed rules")
    lines.extend(
        [
            "",
            "## Concrete Candidate Families",
            "",
        ]
    )
    for row in summary_rows[:25]:
        lines.extend(
            [
                f"### d={row['d']}, pair=({row['a']},{row['b']}), q={row['q']}",
                "",
                f"- template: `{row['template']}`",
                f"- support_count: `{row['support_count']}`",
                f"- lcm(a,b): `{row['lcm_a_b']} = {row['lcm_a_b_factorization']}`",
                f"- rule residues modulo q: `{row['residue_set']}`",
                f"- local prime-power conditions: `{row['prime_power_local_conditions']}`",
                f"- hard-core n == 1 mod 24 residues modulo dominant p: `{row['hard_core_residues_mod_p']}`",
                f"- hard-core condition equals {{0,-d}} mod p: `{row['hard_core_matches_{0,-d}_mod_p']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Test Summary",
            "",
            f"Prime-power factorization tests passed: `{prime_power_passed}`.",
            f"Prime-power factorization tests failed: `{prime_power_failed}`.",
            f"Hard-core dominant-prime reductions found: `{hard_reductions}`.",
            "",
            "Important: these are local family lemmas and diagnostics. They do",
            "not prove that the remaining core is fully covered.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("prime_factor_family_candidate_lemmas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(summary_rows: list[dict[str, object]], test_rows: list[dict[str, object]]) -> None:
    top_templates = Counter(row["template"] for row in summary_rows)
    top_primes = Counter(row["dominant_prime"] for row in summary_rows if row["dominant_prime"] != "")
    hard_simple = sum(1 for row in summary_rows if row["hard_core_matches_{0,-d}_mod_p"] is True)
    prime_power_failed = sum(
        1
        for row in test_rows
        if row["test_type"] == "prime_power_factorization_equals_direct_rule_set"
        and row["status"] == "failed"
    )
    lines = [
        "# Prime-Factor Family Report",
        "",
        f"Rules analyzed: `{len(summary_rows)}`.",
        f"Template distribution: `{top_templates.most_common()}`.",
        f"Top dominant primes: `{top_primes.most_common(15)}`.",
        f"Hard-core reductions matching `{{0,-d}} mod p`: `{hard_simple}`.",
        f"Prime-power factorization failures: `{prime_power_failed}`.",
        "",
        "The useful mathematical pattern is not a single congruence `n == c mod p`,",
        "but a factorized rule condition: `n+d == 0 mod 4` plus local",
        "prime-power divisibility of `n(n+d)`. For many common rules, after",
        "restricting to the hard core `n == 1 mod 24`, the large-prime part",
        "often reduces to `n == 0 or -d mod p`.",
        "",
        "This suggests the next lemma should classify when the small factors",
        "of `lcm(a,b)` are automatic on `n == 1 mod 24`, leaving only a large",
        "prime condition.",
        "",
        "Verdict: not proved yet.",
    ]
    Path("prime_factor_family_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    missing = [path for path in INPUTS if not path.exists()]
    for path in missing:
        print(f"warning: input missing: {path}")
    counts = load_rule_counts()
    known_sets = load_known_residue_sets()
    summary_rows, test_rows = analyze_rules(counts, known_sets, limit=250)
    write_csv(
        Path("prime_factor_family_summary.csv"),
        [
            "d",
            "a",
            "b",
            "q",
            "lcm_a_b",
            "lcm_a_b_factorization",
            "support_count",
            "template",
            "dominant_prime",
            "residue_count",
            "residue_set",
            "prime_power_local_conditions",
            "hard_core_residues_mod_p",
            "hard_core_matches_{0,-d}_mod_p",
        ],
        summary_rows,
    )
    write_csv(
        Path("prime_factor_family_tests.csv"),
        [
            "d",
            "a",
            "b",
            "q",
            "template",
            "dominant_prime",
            "test_type",
            "tested_modulus",
            "passed",
            "status",
            "details",
        ],
        test_rows,
    )
    write_markdown(summary_rows, test_rows)
    write_report(summary_rows, test_rows)

    template_counts = Counter(row["template"] for row in summary_rows)
    hard_simple = sum(1 for row in summary_rows if row["hard_core_matches_{0,-d}_mod_p"] is True)
    prime_power_passed = sum(
        1
        for row in test_rows
        if row["test_type"] == "prime_power_factorization_equals_direct_rule_set"
        and row["status"] == "passed"
    )
    prime_power_failed = sum(
        1
        for row in test_rows
        if row["test_type"] == "prime_power_factorization_equals_direct_rule_set"
        and row["status"] == "failed"
    )
    print(f"Rules analyzed: {len(summary_rows)}")
    print(f"Top templates: {template_counts.most_common(10)}")
    print(f"Hard-core reductions matching {{0,-d}} mod p: {hard_simple}")
    print(f"Prime-power factorization tests passed: {prime_power_passed}")
    print(f"Prime-power factorization tests failed: {prime_power_failed}")
    print("Best next direction: prove when small prime-power factors are automatic on n == 1 mod 24, leaving a dominant-prime condition.")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
