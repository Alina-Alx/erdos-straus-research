#!/usr/bin/env python3
"""Look for family lemmas where only one prime condition remains.

The previous prime-factor analysis showed that many useful rules have one
dominant prime p in lcm(a,b).  This script asks a narrower mathematical
question:

    On the hard core n == 1 mod 24, are all non-p factors automatic?

If yes, the rule reduces to the simple prime condition

    n == 0 mod p  or  n == -d mod p.

This is a lemma-search tool, not a proof of the full Erdos-Straus conjecture.
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUMMARY_INPUT = Path("prime_factor_family_summary.csv")
RULE_SUMMARY_INPUT = Path("symbolic_rule_summary.csv")


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


def factorization(value: int) -> tuple[tuple[int, int], ...]:
    if value <= 1:
        return ()
    factors: list[tuple[int, int]] = []
    n = value
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


def prime_power(prime: int, exponent: int) -> int:
    return prime**exponent


def is_prime(value: int) -> bool:
    return value > 1 and factorization(value) == ((value, 1),)


def rule_works_on_residue(rule: Rule, residue: int) -> bool:
    if not rule.pair_sum_ok:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


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


def load_support_counts() -> Counter[Rule]:
    counts: Counter[Rule] = Counter()
    if RULE_SUMMARY_INPUT.exists():
        for row in read_csv_rows(RULE_SUMMARY_INPUT):
            rule = Rule(int(row["d"]), int(row["a"]), int(row["b"]))
            counts[rule] += int(float(row.get("diagnostic_leaf_count") or 1))
    if SUMMARY_INPUT.exists():
        for row in read_csv_rows(SUMMARY_INPUT):
            rule = Rule(int(row["d"]), int(row["a"]), int(row["b"]))
            counts[rule] += int(row.get("support_count") or 1)
    return counts


def dominant_prime_from_rule(rule: Rule) -> int | None:
    factors = factorization(rule.l_ab)
    candidates = [prime for prime, exponent in factors if exponent == 1 and prime > 3]
    if not candidates:
        return None
    return max(candidates)


def template_for_rule(rule: Rule, p: int | None) -> str:
    if p is None:
        return "no_dominant_prime"
    if rule.a == 1 and rule.b == p and p == 4 * rule.d - 1:
        return "F1: a=1, b=p=4d-1"
    if rule.a == 2 and rule.b == 2 * p and p == 2 * rule.d - 1:
        return "F2: a=2, b=2p, p=2d-1"
    if rule.a == 3 and rule.b == p and p == 4 * rule.d - 3:
        return "F3: a=3, b=p=4d-3"
    if rule.a == 6 and rule.b == 2 * p and p == 2 * rule.d - 3:
        return "F4: a=6, b=2p, p=2d-3"
    if rule.a == 24 and rule.b == 4 * p and p == rule.d - 6:
        return "F5: a=24, b=4p, p=d-6"
    return "G: one dominant prime factor"


def non_dominant_prime_powers(rule: Rule, p: int | None) -> list[int]:
    powers: list[int] = []
    for prime, exponent in factorization(rule.l_ab):
        if p is not None and prime == p:
            continue
        powers.append(prime_power(prime, exponent))
    return powers


def local_factor_is_automatic_on_1_mod_24(rule: Rule, modulus: int) -> bool:
    """Check if n == 1 mod 24 implies modulus | n(n+d)."""
    test_modulus = lcm_many(24, modulus)
    for residue in range(1, test_modulus, 24):
        if (residue * (residue + rule.d)) % modulus != 0:
            return False
    return True


def prime_condition_is_enough(rule: Rule, p: int, small_powers: list[int]) -> bool:
    """Verify hard-core + prime condition implies the full rule.

    This is a finite residue check modulo lcm(24, p, q). It is exact for the
    stated residue-class formulation.
    """
    test_modulus = lcm_many(24, p, rule.q)
    allowed_mod_p = {0, (-rule.d) % p}
    for residue in range(test_modulus):
        if residue % 24 != 1:
            continue
        if residue % p not in allowed_mod_p:
            continue
        if not rule_works_on_residue(rule, residue % rule.q):
            return False
    return all(local_factor_is_automatic_on_1_mod_24(rule, power) for power in small_powers)


def automatic_reason(rule: Rule, modulus: int) -> str:
    factors = factorization(modulus)
    if factors == ((2, 1),):
        return "n is odd and d is odd, so n+d is even"
    if factors and factors[0][0] == 2:
        return f"n == 1 mod {modulus} and d == {-1 % modulus} mod {modulus}"
    if factors == ((3, 1),):
        return "n == 1 mod 3 and d == 2 mod 3"
    return f"checked exactly modulo lcm(24,{modulus})"


def infer_template_parameter_lemma(template: str) -> tuple[str, str]:
    if template.startswith("F1"):
        return (
            "If d == 3 mod 4 and p=4d-1 is prime, then for n == 1 mod 24 "
            "the rule (d,1,p) works whenever n == 0 or -d mod p.",
            "No small a/b factors remain after p.",
        )
    if template.startswith("F2"):
        return (
            "If d == 3 mod 4 and p=2d-1 is prime, then for n == 1 mod 24 "
            "the rule (d,2,2p) works whenever n == 0 or -d mod p.",
            "The factor 2 is automatic because n and d are odd.",
        )
    if template.startswith("F3"):
        return (
            "If d == 11 mod 12 and p=4d-3 is prime, then for n == 1 mod 24 "
            "the rule (d,3,p) works whenever n == 0 or -d mod p.",
            "The factor 3 is automatic because n == 1 mod 3 and d == 2 mod 3.",
        )
    if template.startswith("F4"):
        return (
            "If d == 11 mod 12 and p=2d-3 is prime, then for n == 1 mod 24 "
            "the rule (d,6,2p) works whenever n == 0 or -d mod p.",
            "The factors 2 and 3 are automatic.",
        )
    if template.startswith("F5"):
        return (
            "If d == 23 mod 24 and p=d-6 is prime, then for n == 1 mod 24 "
            "the rule (d,24,4p) works whenever n == 0 or -d mod p.",
            "The factors 8 and 3 are automatic because n+d == 0 mod 24.",
        )
    return (
        "For a fixed dominant-prime rule, if every non-p prime-power factor "
        "of lcm(a,b) is automatic on n == 1 mod 24, then only the condition "
        "n == 0 or -d mod p remains.",
        "This is exact for each listed rule, but not yet a single closed-form family.",
    )


def analyze_rules(counts: Counter[Rule], limit: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    family_rows: list[dict[str, object]] = []
    family_support: defaultdict[str, int] = defaultdict(int)
    family_passed: defaultdict[str, int] = defaultdict(int)
    family_examples: defaultdict[str, list[str]] = defaultdict(list)

    for rule, support in counts.most_common(limit):
        if not rule.pair_sum_ok:
            continue
        p = dominant_prime_from_rule(rule)
        template = template_for_rule(rule, p)
        small_powers = non_dominant_prime_powers(rule, p)
        automatic_powers = [
            power for power in small_powers if local_factor_is_automatic_on_1_mod_24(rule, power)
        ]
        nonautomatic_powers = [power for power in small_powers if power not in automatic_powers]
        prime_reduction_passed = bool(p) and not nonautomatic_powers and prime_condition_is_enough(
            rule, p, small_powers
        )

        family_support[template] += support
        if prime_reduction_passed:
            family_passed[template] += 1
        if len(family_examples[template]) < 8:
            family_examples[template].append(f"d={rule.d}, a={rule.a}, b={rule.b}, p={p}")

        rows.append(
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
                "small_prime_powers": ";".join(str(x) for x in small_powers),
                "automatic_small_prime_powers": ";".join(str(x) for x in automatic_powers),
                "nonautomatic_small_prime_powers": ";".join(str(x) for x in nonautomatic_powers),
                "prime_condition": "" if not p else f"n mod {p} in {{0,{(-rule.d) % p}}}",
                "prime_condition_enough_on_n_1_mod_24": prime_reduction_passed,
                "automatic_reasons": "; ".join(automatic_reason(rule, power) for power in automatic_powers),
            }
        )

    for template, support in sorted(family_support.items(), key=lambda item: item[1], reverse=True):
        claim, reason = infer_template_parameter_lemma(template)
        related = [row for row in rows if row["template"] == template]
        passed = sum(1 for row in related if row["prime_condition_enough_on_n_1_mod_24"] is True)
        failed = len(related) - passed
        family_rows.append(
            {
                "template": template,
                "rules_seen": len(related),
                "rules_prime_reduction_passed": passed,
                "rules_not_reduced": failed,
                "support_count": support,
                "candidate_family_claim": claim,
                "why_small_factors_are_automatic": reason,
                "examples": " | ".join(family_examples[template]),
            }
        )

    return rows, family_rows


def write_markdown(rows: list[dict[str, object]], family_rows: list[dict[str, object]]) -> None:
    passed = [row for row in rows if row["prime_condition_enough_on_n_1_mod_24"] is True]
    failed = [row for row in rows if row["prime_condition_enough_on_n_1_mod_24"] is not True]
    top_nonautomatic = Counter()
    for row in failed:
        for value in str(row["nonautomatic_small_prime_powers"]).split(";"):
            if value:
                top_nonautomatic[value] += 1

    lines = [
        "# Automatic Small-Factor Lemma Search",
        "",
        "This report searches for family lemmas of the form:",
        "",
        "`n == 1 mod 24` plus `n == 0 or -d mod p` implies a fixed",
        "general-key rule `(d,a,b)`.",
        "",
        "It does not prove the full Erdos-Straus conjecture.",
        "",
        "## Summary",
        "",
        f"- rules analyzed: `{len(rows)}`",
        f"- rules reduced to one dominant-prime condition: `{len(passed)}`",
        f"- rules not reduced by this test: `{len(failed)}`",
        f"- common nonautomatic small factors: `{top_nonautomatic.most_common(15)}`",
        "",
        "## Family Candidates",
        "",
    ]
    for row in family_rows:
        lines.extend(
            [
                f"### {row['template']}",
                "",
                f"- rules seen: `{row['rules_seen']}`",
                f"- rules reduced: `{row['rules_prime_reduction_passed']}`",
                f"- support count: `{row['support_count']}`",
                f"- claim: {row['candidate_family_claim']}",
                f"- automatic factor reason: {row['why_small_factors_are_automatic']}",
                f"- examples: `{row['examples']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
            "The F1-F5 templates are the cleanest human-readable candidates.",
            "They explain many repeated rules by reducing all divisibility checks",
            "to one prime condition.  The broader G family is mixed: it often has",
            "extra factors such as 5, 7, 11, 13, or 17 that are not forced by",
            "`n == 1 mod 24`, so those rules need either additional hypotheses or",
            "a different family lemma.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("automatic_small_factor_lemma_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_candidate_lemmas(family_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Candidate Family Lemmas by Prime Factors",
        "",
        "These are candidate local lemmas for the hard core `n == 1 mod 24`.",
        "Each lemma still needs independent mathematical review. They are not a",
        "proof of the full Erdos-Straus conjecture.",
        "",
    ]
    lemma_id = 1
    for row in family_rows:
        if int(row["rules_prime_reduction_passed"]) == 0:
            continue
        lines.extend(
            [
                f"## Lemma candidate {lemma_id}: {row['template']}",
                "",
                f"Claim: {row['candidate_family_claim']}",
                "",
                f"Why it might work: {row['why_small_factors_are_automatic']}",
                "",
                "Conclusion:",
                "",
                "```text",
                "x = (n+d)/4",
                "y = n(n+d)/a",
                "z = n(n+d)/b",
                "```",
                "",
                "Status: algebraically verified for the listed fixed rules by finite",
                "residue tests; conjectural as a reusable family until reviewed by hand.",
                "",
            ]
        )
        lemma_id += 1
    lines.extend(
        [
            "## Guardrail",
            "",
            "No full proof is claimed here. These lemmas only describe local",
            "rule families that may help compress the remaining core.",
        ]
    )
    Path("automatic_small_factor_candidate_lemmas.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    missing = [path for path in (SUMMARY_INPUT, RULE_SUMMARY_INPUT) if not path.exists()]
    for path in missing:
        print(f"warning: input missing: {path}")

    counts = load_support_counts()
    rows, family_rows = analyze_rules(counts, limit=500)

    write_csv(
        Path("automatic_small_factor_rules.csv"),
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
            "small_prime_powers",
            "automatic_small_prime_powers",
            "nonautomatic_small_prime_powers",
            "prime_condition",
            "prime_condition_enough_on_n_1_mod_24",
            "automatic_reasons",
        ],
        rows,
    )
    write_csv(
        Path("automatic_small_factor_family_summary.csv"),
        [
            "template",
            "rules_seen",
            "rules_prime_reduction_passed",
            "rules_not_reduced",
            "support_count",
            "candidate_family_claim",
            "why_small_factors_are_automatic",
            "examples",
        ],
        family_rows,
    )
    write_markdown(rows, family_rows)
    write_candidate_lemmas(family_rows)

    passed = sum(1 for row in rows if row["prime_condition_enough_on_n_1_mod_24"] is True)
    template_counts = Counter(row["template"] for row in rows)
    reduced_by_template = Counter(
        row["template"] for row in rows if row["prime_condition_enough_on_n_1_mod_24"] is True
    )
    top_nonautomatic = Counter()
    for row in rows:
        for value in str(row["nonautomatic_small_prime_powers"]).split(";"):
            if value:
                top_nonautomatic[value] += 1

    print(f"Rules analyzed: {len(rows)}")
    print(f"Rules reduced to one prime condition: {passed}")
    print(f"Template distribution: {template_counts.most_common(10)}")
    print(f"Reduced by template: {reduced_by_template.most_common(10)}")
    print(f"Top nonautomatic small factors: {top_nonautomatic.most_common(10)}")
    print("Best next direction: use F1-F5 as hand-checkable family lemmas, then isolate the G rules with nonautomatic factors.")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
