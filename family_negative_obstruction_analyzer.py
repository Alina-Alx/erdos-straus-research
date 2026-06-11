#!/usr/bin/env python3
"""Explain why direct negative-family forcing usually fails.

This reads ``family_negative_implication_attempts.csv`` and looks for the
dominant obstruction: target family conditions often introduce fresh prime
moduli that are independent of the negative assumptions.  In that situation,
CRT typically supplies counterexamples instead of forcing.

This is an obstruction/diagnostic tool, not a proof of the conjecture.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path

from compound_symbolic_cover import load_family_rules


ATTEMPTS = Path("family_negative_implication_attempts.csv")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def label_for(d: int, a: int, b: int) -> str:
    return f"d={d},a={a},b={b}"


def labels_in_text(text: str) -> list[str]:
    return [
        label_for(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        for match in re.finditer(r"d=(\d+),a=(\d+),b=(\d+)", text)
    ]


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


def rule_moduli_map() -> dict[str, set[int]]:
    mapping: dict[str, set[int]] = {}
    for rule in load_family_rules(500):
        mapping[rule.key] = {condition.modulus for condition in rule.conditions if condition.modulus != 24}
    return mapping


def analyze() -> tuple[list[dict[str, object]], list[str]]:
    if not ATTEMPTS.exists():
        raise FileNotFoundError(f"missing {ATTEMPTS}; run family_negative_implication_finder.py first")

    moduli_by_rule = rule_moduli_map()
    rows = read_csv_rows(ATTEMPTS)
    status_counts = Counter(row["status"] for row in rows)
    fresh_moduli_counts: Counter[str] = Counter()
    fresh_prime_counts: Counter[int] = Counter()
    pattern_counts: Counter[tuple[str, str, str]] = Counter()
    detail_rows: list[dict[str, object]] = []

    for row in rows:
        negative_labels = labels_in_text(row["negative_rules"])
        target_labels = labels_in_text(row["target_rule"])
        if not target_labels:
            continue
        target_label = target_labels[0]
        negative_moduli: set[int] = set()
        for label in negative_labels:
            negative_moduli.update(moduli_by_rule.get(label, set()))
        target_moduli = moduli_by_rule.get(target_label, set())
        fresh_moduli = {
            modulus
            for modulus in target_moduli
            if all(math.gcd(modulus, existing) == 1 for existing in negative_moduli)
        }
        fresh_text = ";".join(str(modulus) for modulus in sorted(fresh_moduli))
        if fresh_text:
            fresh_moduli_counts[fresh_text] += 1
            for modulus in fresh_moduli:
                for prime in factorization(modulus):
                    fresh_prime_counts[prime] += 1
        pattern_counts[(row["status"], row["negative_rules"], row["target_rule"])] += 1
        if len(detail_rows) < 5000:
            detail_rows.append(
                {
                    "status": row["status"],
                    "focus_r": row["focus_r"],
                    "depth": row["depth"],
                    "negative_rules": row["negative_rules"],
                    "target_rule": row["target_rule"],
                    "negative_moduli": ";".join(str(x) for x in sorted(negative_moduli)),
                    "target_moduli": ";".join(str(x) for x in sorted(target_moduli)),
                    "fresh_target_moduli": fresh_text,
                    "refinement_ratio": row["refinement_ratio"],
                    "counterexample_residue": row["counterexample_residue"],
                }
            )

    lines = [
        "# Family Negative-Condition Obstruction Report",
        "",
        "This report explains why direct implications such as",
        "`Base AND NOT(A) => B` did not appear in the sampled search.",
        "",
        "## Summary",
        "",
        f"- attempts analyzed: `{len(rows)}`",
        f"- status counts: `{status_counts.most_common()}`",
        f"- top fresh target moduli: `{fresh_moduli_counts.most_common(15)}`",
        f"- top fresh target primes: `{fresh_prime_counts.most_common(15)}`",
        "",
        "## Obstruction Lemma Candidate",
        "",
        "Claim shape:",
        "",
        "```text",
        "If the target family condition contains a modulus q_target that is",
        "coprime to all moduli appearing in the base/negative assumptions,",
        "then the negative assumptions usually cannot force the target.",
        "CRT supplies residues satisfying the negatives while avoiding target.",
        "```",
        "",
        "Status: computationally supported by the failed/unknown implication",
        "attempts. This is an obstruction lemma, not a cover lemma.",
        "",
        "## Consequence",
        "",
        "A successful next lemma probably cannot be only:",
        "",
        "```text",
        "NOT(rule_1) AND NOT(rule_2) => rule_3",
        "```",
        "",
        "It must either:",
        "",
        "- group rules by shared prime moduli, so the target prime is not fresh;",
        "- use a covering statement over a fixed small prime set;",
        "- or prove a structural reason that the base class already restricts",
        "  the target prime.",
        "",
        "Verdict: not proved yet.",
    ]
    Path("family_negative_obstruction_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return detail_rows, lines


def main() -> None:
    detail_rows, _lines = analyze()
    write_csv(
        Path("family_negative_obstruction_details.csv"),
        [
            "status",
            "focus_r",
            "depth",
            "negative_rules",
            "target_rule",
            "negative_moduli",
            "target_moduli",
            "fresh_target_moduli",
            "refinement_ratio",
            "counterexample_residue",
        ],
        detail_rows,
    )
    print("Wrote family_negative_obstruction_report.md")
    print("Wrote family_negative_obstruction_details.csv")
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
