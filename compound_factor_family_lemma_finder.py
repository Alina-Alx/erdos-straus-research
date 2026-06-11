#!/usr/bin/env python3
"""Group remaining dominant-prime rules by their extra small-factor conditions.

The clean F1-F5 families reduce to a single dominant-prime condition on the
hard core n == 1 mod 24.  The leftover G rules often need one or two extra
conditions modulo small prime powers such as 5, 7, 9, 16, or 13.

This script writes those compound local lemmas in a readable form:

    n == 1 mod 24
    n mod p in {0, -d}
    n mod h_i in S_i for each nonautomatic small factor h_i

It is a compression and lemma-discovery tool, not a proof of the full
Erdos-Straus conjecture.
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INPUT = Path("automatic_small_factor_rules.csv")


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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rule_works_on_residue(rule: Rule, residue: int) -> bool:
    if rule.a + rule.b != 4 * rule.d:
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


def parse_int_list(text: str) -> list[int]:
    if not text:
        return []
    return [int(part) for part in text.split(";") if part]


def local_residue_set(d: int, modulus: int) -> set[int]:
    return {
        residue
        for residue in range(modulus)
        if (residue * (residue + d)) % modulus == 0
    }


def condition_text(d: int, modulus: int) -> str:
    residues = sorted(local_residue_set(d, modulus))
    simple = sorted({0, (-d) % modulus})
    if residues == simple:
        return f"n mod {modulus} in {{0,{(-d) % modulus}}}"
    return f"n mod {modulus} in {{{';'.join(str(x) for x in residues)}}}"


def compound_conditions_are_enough(rule: Rule, p: int, extra_moduli: list[int]) -> bool:
    conditions: list[tuple[int, set[int]]] = [
        (24, {1}),
        (p, {0, (-rule.d) % p}),
    ]
    for modulus in extra_moduli:
        conditions.append((modulus, local_residue_set(rule.d, modulus)))

    test_modulus = lcm_many(rule.q, *(modulus for modulus, _residues in conditions))
    for residue in range(test_modulus):
        if all(residue % modulus in residues for modulus, residues in conditions):
            if not rule_works_on_residue(rule, residue % rule.q):
                return False
    return True


def analyze() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not INPUT.exists():
        raise FileNotFoundError(f"missing required input: {INPUT}")

    rows: list[dict[str, object]] = []
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)

    for input_row in read_csv_rows(INPUT):
        if input_row["template"] != "G: one dominant prime factor":
            continue
        if input_row["prime_condition_enough_on_n_1_mod_24"] == "True":
            continue

        rule = Rule(int(input_row["d"]), int(input_row["a"]), int(input_row["b"]))
        p = int(input_row["dominant_prime"])
        extra_moduli = parse_int_list(input_row["nonautomatic_small_prime_powers"])
        if not extra_moduli:
            continue

        condition_parts = [condition_text(rule.d, modulus) for modulus in extra_moduli]
        passed = compound_conditions_are_enough(rule, p, extra_moduli)
        combo = ";".join(str(x) for x in extra_moduli)
        row = {
            "d": rule.d,
            "a": rule.a,
            "b": rule.b,
            "q": rule.q,
            "dominant_prime": p,
            "support_count": int(input_row["support_count"]),
            "extra_moduli": combo,
            "extra_condition_count": len(extra_moduli),
            "prime_condition": f"n mod {p} in {{0,{(-rule.d) % p}}}",
            "extra_conditions": " AND ".join(condition_parts),
            "compound_conditions_enough": passed,
            "status": "passed" if passed else "failed",
        }
        rows.append(row)
        grouped[combo].append(row)

    summary_rows: list[dict[str, object]] = []
    for combo, group in sorted(
        grouped.items(),
        key=lambda item: sum(int(row["support_count"]) for row in item[1]),
        reverse=True,
    ):
        support = sum(int(row["support_count"]) for row in group)
        passed = sum(1 for row in group if row["compound_conditions_enough"] is True)
        examples = " | ".join(
            f"d={row['d']}, pair=({row['a']},{row['b']}), p={row['dominant_prime']}, {row['extra_conditions']}"
            for row in group[:6]
        )
        summary_rows.append(
            {
                "extra_moduli": combo,
                "rules_seen": len(group),
                "rules_passed": passed,
                "rules_failed": len(group) - passed,
                "support_count": support,
                "examples": examples,
            }
        )

    return rows, summary_rows


def write_markdown(rows: list[dict[str, object]], summary_rows: list[dict[str, object]]) -> None:
    passed = sum(1 for row in rows if row["compound_conditions_enough"] is True)
    failed = len(rows) - passed
    extra_counter = Counter()
    for row in rows:
        for value in str(row["extra_moduli"]).split(";"):
            if value:
                extra_counter[value] += 1

    lines = [
        "# Compound Factor Family Lemmas",
        "",
        "This report handles G-family rules that do not reduce to one dominant",
        "prime condition on `n == 1 mod 24`.",
        "",
        "The candidate lemma shape is:",
        "",
        "```text",
        "n == 1 mod 24",
        "n mod p in {0, -d}",
        "n mod h_i in S_i for each extra small factor h_i",
        "```",
        "",
        "where `S_i = {t mod h_i : t(t+d) == 0 mod h_i}`.",
        "",
        "This is still local rule compression, not a proof of the full conjecture.",
        "",
        "## Summary",
        "",
        f"- G rules needing extra conditions: `{len(rows)}`",
        f"- compound local tests passed: `{passed}`",
        f"- compound local tests failed: `{failed}`",
        f"- top extra moduli: `{extra_counter.most_common(15)}`",
        "",
        "## Top Compound Families",
        "",
    ]
    for row in summary_rows[:25]:
        lines.extend(
            [
                f"### extra moduli `{row['extra_moduli']}`",
                "",
                f"- rules seen: `{row['rules_seen']}`",
                f"- rules passed: `{row['rules_passed']}`",
                f"- support count: `{row['support_count']}`",
                f"- examples: `{row['examples']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "The clean next mathematical target is now visible: prove a general",
            "compound lemma that takes the dominant-prime condition plus the local",
            "sets for a small list of extra prime powers.  This replaces explicit",
            "lift enumeration with small modular hypotheses.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("compound_factor_family_lemmas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, summary_rows = analyze()
    write_csv(
        Path("compound_factor_family_rules.csv"),
        [
            "d",
            "a",
            "b",
            "q",
            "dominant_prime",
            "support_count",
            "extra_moduli",
            "extra_condition_count",
            "prime_condition",
            "extra_conditions",
            "compound_conditions_enough",
            "status",
        ],
        rows,
    )
    write_csv(
        Path("compound_factor_family_summary.csv"),
        [
            "extra_moduli",
            "rules_seen",
            "rules_passed",
            "rules_failed",
            "support_count",
            "examples",
        ],
        summary_rows,
    )
    write_markdown(rows, summary_rows)

    passed = sum(1 for row in rows if row["compound_conditions_enough"] is True)
    failed = len(rows) - passed
    combo_counts = Counter(row["extra_moduli"] for row in rows)
    print(f"G rules needing extra conditions: {len(rows)}")
    print(f"Compound local tests passed: {passed}")
    print(f"Compound local tests failed: {failed}")
    print(f"Top extra-moduli combos: {combo_counts.most_common(10)}")
    print("Best next direction: turn these compound local conditions into a symbolic cover over remaining remainders.")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
