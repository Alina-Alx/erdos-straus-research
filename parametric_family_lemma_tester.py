#!/usr/bin/env python3
"""Test clean parametric family lemmas for the hard core n == 1 mod 24.

The families here are conditional local lemmas.  They say that if d has the
right congruence and the indicated p is prime, then a fixed general-key rule
works for all n in the hard core satisfying n == 0 or -d mod p.

This script does finite residue tests for many d values and writes a
human-readable lemma note.  It does not prove the full Erdos-Straus conjecture.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Family:
    name: str
    d_condition: Callable[[int], bool]
    p_from_d: Callable[[int], int]
    a_from_d_p: Callable[[int, int], int]
    b_from_d_p: Callable[[int, int], int]
    claim: str
    proof_note: str


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


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


def is_prime(value: int) -> bool:
    return value > 1 and factorization(value) == ((value, 1),)


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


def rule_works_on_residue(rule: Rule, residue: int) -> bool:
    if rule.a + rule.b != 4 * rule.d:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def families() -> list[Family]:
    return [
        Family(
            name="F1: (a,b)=(1,p), p=4d-1",
            d_condition=lambda d: d % 4 == 3,
            p_from_d=lambda d: 4 * d - 1,
            a_from_d_p=lambda _d, _p: 1,
            b_from_d_p=lambda _d, p: p,
            claim="d == 3 mod 4, p=4d-1 prime, n == 1 mod 24, n == 0 or -d mod p",
            proof_note="No non-p divisibility remains; p divides n(n+d) by the last condition.",
        ),
        Family(
            name="F2: (a,b)=(2,2p), p=2d-1",
            d_condition=lambda d: d % 4 == 3,
            p_from_d=lambda d: 2 * d - 1,
            a_from_d_p=lambda _d, _p: 2,
            b_from_d_p=lambda _d, p: 2 * p,
            claim="d == 3 mod 4, p=2d-1 prime, n == 1 mod 24, n == 0 or -d mod p",
            proof_note="n and d are odd, so n+d is even; p divides n(n+d) by the last condition.",
        ),
        Family(
            name="F3: (a,b)=(3,p), p=4d-3",
            d_condition=lambda d: d % 12 == 11,
            p_from_d=lambda d: 4 * d - 3,
            a_from_d_p=lambda _d, _p: 3,
            b_from_d_p=lambda _d, p: p,
            claim="d == 11 mod 12, p=4d-3 prime, n == 1 mod 24, n == 0 or -d mod p",
            proof_note="n == 1 mod 3 and d == 2 mod 3, so n+d is divisible by 3.",
        ),
        Family(
            name="F4: (a,b)=(6,2p), p=2d-3",
            d_condition=lambda d: d % 12 == 11,
            p_from_d=lambda d: 2 * d - 3,
            a_from_d_p=lambda _d, _p: 6,
            b_from_d_p=lambda _d, p: 2 * p,
            claim="d == 11 mod 12, p=2d-3 prime, n == 1 mod 24, n == 0 or -d mod p",
            proof_note="The factors 2 and 3 divide n+d; p divides n(n+d) by the last condition.",
        ),
        Family(
            name="F5: (a,b)=(24,4p), p=d-6",
            d_condition=lambda d: d % 24 == 23,
            p_from_d=lambda d: d - 6,
            a_from_d_p=lambda _d, _p: 24,
            b_from_d_p=lambda _d, p: 4 * p,
            claim="d == 23 mod 24, p=d-6 prime, n == 1 mod 24, n == 0 or -d mod p",
            proof_note="n+d is divisible by 24; therefore the 24 and 4 factors are automatic.",
        ),
    ]


def test_family_instance(family: Family, d: int) -> dict[str, object] | None:
    if not family.d_condition(d):
        return None
    p = family.p_from_d(d)
    if not is_prime(p):
        return None
    rule = Rule(d=d, a=family.a_from_d_p(d, p), b=family.b_from_d_p(d, p))
    if rule.a + rule.b != 4 * d:
        return {
            "family": family.name,
            "d": d,
            "p": p,
            "a": rule.a,
            "b": rule.b,
            "q": rule.q,
            "tested_classes": 0,
            "passed": False,
            "status": "bad_pair_sum",
            "counterexample": "",
        }

    tested_classes = 0
    counterexample = ""
    for p_residue in sorted({0, (-d) % p}):
        intersection = crt_intersection(24, 1, p, p_residue)
        if intersection is None:
            counterexample = f"no CRT intersection for p_residue={p_residue}"
            break
        modulus, residue = intersection
        tested_classes += 1
        test_modulus = lcm_many(modulus, rule.q)
        for candidate in range(residue, test_modulus, modulus):
            if not rule_works_on_residue(rule, candidate % rule.q):
                counterexample = f"n == {candidate} mod {test_modulus}"
                break
        if counterexample:
            break

    return {
        "family": family.name,
        "d": d,
        "p": p,
        "a": rule.a,
        "b": rule.b,
        "q": rule.q,
        "tested_classes": tested_classes,
        "passed": not counterexample,
        "status": "passed" if not counterexample else "failed",
        "counterexample": counterexample,
    }


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, object]], max_d: int) -> None:
    by_family: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_family.setdefault(str(row["family"]), []).append(row)

    lines = [
        "# Parametric Family Lemma Tests",
        "",
        f"Tested all matching prime-parameter instances with `d <= {max_d}`.",
        "",
        "These are conditional local lemmas for `n == 1 mod 24`; they do not",
        "prove the full Erdős-Straus conjecture.",
        "",
    ]
    for family in families():
        family_rows = by_family.get(family.name, [])
        passed = sum(1 for row in family_rows if row["passed"] is True)
        failed = len(family_rows) - passed
        examples = ", ".join(
            f"d={row['d']}, p={row['p']}" for row in family_rows[:8]
        )
        lines.extend(
            [
                f"## {family.name}",
                "",
                f"Claim: `{family.claim}`.",
                "",
                f"Proof idea: {family.proof_note}",
                "",
                f"Instances tested: `{len(family_rows)}`.",
                f"Passed: `{passed}`.",
                f"Failed: `{failed}`.",
                f"Examples: `{examples}`.",
                "",
                "Algebraic shape:",
                "",
                "```text",
                "x = (n+d)/4",
                "y = n(n+d)/a",
                "z = n(n+d)/b",
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Verdict",
            "",
            "These tests support the family lemmas above, and the proof notes are",
            "simple enough to check by hand.  They are still local compression",
            "lemmas for the hard core, not a full proof certificate.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("parametric_family_lemmas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-d", type=int, default=20_000)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for family in families():
        for d in range(1, args.max_d + 1):
            row = test_family_instance(family, d)
            if row is not None:
                rows.append(row)

    write_csv(
        Path("parametric_family_tests.csv"),
        [
            "family",
            "d",
            "p",
            "a",
            "b",
            "q",
            "tested_classes",
            "passed",
            "status",
            "counterexample",
        ],
        rows,
    )
    write_markdown(rows, args.max_d)

    total_passed = sum(1 for row in rows if row["passed"] is True)
    total_failed = len(rows) - total_passed
    print(f"Parametric family instances tested: {len(rows)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    for family in families():
        family_rows = [row for row in rows if row["family"] == family.name]
        passed = sum(1 for row in family_rows if row["passed"] is True)
        print(f"{family.name}: {passed}/{len(family_rows)} passed")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
