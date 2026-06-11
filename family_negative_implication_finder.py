#!/usr/bin/env python3
"""Search for implications between negative family conditions.

The previous step showed that every remaining base class is touched by a
compound family condition, but only partially.  This script asks the next
question:

    Base AND NOT(A)  =>  B ?
    Base AND NOT(A) AND NOT(B)  =>  C ?

Here A, B, C are positive family conditions, such as:

    n == 1 mod 24
    n mod p in {0, -d}
    n mod h in S_h

The checks are finite residue tests modulo the lcm of the base class and the
condition moduli.  Large refinements are marked unknown.  This is not a proof
of the Erdos-Straus conjecture.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from compound_symbolic_cover import (
    FOCUS_RESIDUES,
    FamilyRule,
    RemainderClass,
    load_family_rules,
    load_remainders,
    lcm_many,
)


@dataclass(frozen=True)
class ImplicationResult:
    status: str
    verified_modulus: int
    refinement_ratio: int
    antecedent_count: int
    counterexample_residue: int | None
    reason: str


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rule_label(rule: FamilyRule) -> str:
    return f"d={rule.d},a={rule.a},b={rule.b}"


def rule_condition_holds(rule: FamilyRule, n: int) -> bool:
    return all(n % condition.modulus in condition.residues for condition in rule.conditions)


def implication_modulus(base: RemainderClass, negatives: tuple[FamilyRule, ...], target: FamilyRule) -> int:
    modulus = base.base_modulus
    for rule in (*negatives, target):
        for condition in rule.conditions:
            modulus = lcm_many(modulus, condition.modulus)
    return modulus


def test_negative_implication(
    base: RemainderClass,
    negatives: tuple[FamilyRule, ...],
    target: FamilyRule,
    max_ratio: int,
) -> ImplicationResult:
    modulus = implication_modulus(base, negatives, target)
    ratio = modulus // base.base_modulus
    if ratio > max_ratio:
        return ImplicationResult(
            status="unknown_large_ratio",
            verified_modulus=modulus,
            refinement_ratio=ratio,
            antecedent_count=-1,
            counterexample_residue=None,
            reason=f"ratio {ratio} exceeds max_ratio {max_ratio}",
        )

    antecedent_count = 0
    for residue in range(base.base_residue % modulus, modulus, base.base_modulus):
        if any(rule_condition_holds(rule, residue) for rule in negatives):
            continue
        antecedent_count += 1
        if not rule_condition_holds(target, residue):
            return ImplicationResult(
                status="failed",
                verified_modulus=modulus,
                refinement_ratio=ratio,
                antecedent_count=antecedent_count,
                counterexample_residue=residue,
                reason="antecedent has residue not covered by target",
            )

    if antecedent_count == 0:
        return ImplicationResult(
            status="vacuous",
            verified_modulus=modulus,
            refinement_ratio=ratio,
            antecedent_count=0,
            counterexample_residue=None,
            reason="negative assumptions leave no residue in this finite class",
        )
    return ImplicationResult(
        status="forced",
        verified_modulus=modulus,
        refinement_ratio=ratio,
        antecedent_count=antecedent_count,
        counterexample_residue=None,
        reason="all antecedent residues satisfy target family condition",
    )


def rule_intersects_base(base: RemainderClass, rule: FamilyRule) -> bool:
    # A cheap exact test for existence; condition sets are tiny.
    modulus = base.base_modulus
    residues = {base.base_residue % base.base_modulus}
    for condition in rule.conditions:
        next_modulus = lcm_many(modulus, condition.modulus)
        next_residues: set[int] = set()
        for left in residues:
            for right in condition.residues:
                # Inline CRT existence by scanning only tiny condition sets via congruence.
                common = __import__("math").gcd(modulus, condition.modulus)
                if (right - left) % common != 0:
                    continue
                reduced_m1 = modulus // common
                reduced_m2 = condition.modulus // common
                step = ((right - left) // common * pow(reduced_m1, -1, reduced_m2)) % reduced_m2
                next_residues.add((left + modulus * step) % next_modulus)
        if not next_residues:
            return False
        modulus = next_modulus
        residues = next_residues
    return True


def candidate_rules_for_base(base: RemainderClass, rules: list[FamilyRule], limit: int) -> list[FamilyRule]:
    candidates: list[FamilyRule] = []
    for rule in rules:
        if rule_intersects_base(base, rule):
            candidates.append(rule)
            if len(candidates) >= limit:
                break
    return candidates


def analyze_focus(
    focus_r: int,
    rules: list[FamilyRule],
    sample_limit: int,
    max_ratio: int,
    candidate_limit: int,
    search_depth: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    remainders = load_remainders(focus_r, sample_limit)
    rows: list[dict[str, object]] = []
    attempt_rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    implication_counts: Counter[tuple[str, str]] = Counter()
    processed = 0
    no_candidate = 0

    for base in remainders:
        processed += 1
        candidates = candidate_rules_for_base(base, rules, candidate_limit)
        if len(candidates) < 2:
            no_candidate += 1
            continue

        found_for_base = False
        max_depth_for_base = min(search_depth, len(candidates) - 1)
        for depth in range(1, max_depth_for_base + 1):
            negatives = tuple(candidates[:depth])
            negative_label = "; ".join(rule_label(rule) for rule in negatives)
            for target in candidates[depth:]:
                result = test_negative_implication(base, negatives, target, max_ratio)
                status_counts[result.status] += 1
                if len(attempt_rows) < 50_000:
                    attempt_rows.append(
                        {
                            "focus_r": focus_r,
                            "base_modulus": base.base_modulus,
                            "base_residue": base.base_residue,
                            "depth": depth,
                            "negative_rules": negative_label,
                            "target_rule": rule_label(target),
                            "status": result.status,
                            "verified_modulus": result.verified_modulus,
                            "refinement_ratio": result.refinement_ratio,
                            "antecedent_count": result.antecedent_count,
                            "counterexample_residue": result.counterexample_residue or "",
                            "reason": result.reason,
                        }
                    )
                if result.status != "forced":
                    continue
                implication_counts[(negative_label, rule_label(target))] += 1
                rows.append(
                    {
                        "focus_r": focus_r,
                        "base_modulus": base.base_modulus,
                        "base_residue": base.base_residue,
                        "depth": depth,
                        "negative_rules": negative_label,
                        "target_rule": rule_label(target),
                        "status": result.status,
                        "verified_modulus": result.verified_modulus,
                        "refinement_ratio": result.refinement_ratio,
                        "antecedent_count": result.antecedent_count,
                        "counterexample_residue": result.counterexample_residue or "",
                        "reason": result.reason,
                    }
                )
                found_for_base = True
                break
            if found_for_base:
                break

        if found_for_base:
            continue

        # Record vacuous prefix contradictions separately; they are useful
        # diagnostics but not positive forcing lemmas.
        for depth in range(2, max_depth_for_base + 1):
            negatives = tuple(candidates[:depth])
            target = candidates[depth]
            result = test_negative_implication(base, negatives, target, max_ratio)
            status_counts[result.status] += 1
            if len(attempt_rows) < 50_000:
                negative_label = "; ".join(rule_label(rule) for rule in negatives)
                attempt_rows.append(
                    {
                        "focus_r": focus_r,
                        "base_modulus": base.base_modulus,
                        "base_residue": base.base_residue,
                        "depth": depth,
                        "negative_rules": negative_label,
                        "target_rule": rule_label(target),
                        "status": result.status,
                        "verified_modulus": result.verified_modulus,
                        "refinement_ratio": result.refinement_ratio,
                        "antecedent_count": result.antecedent_count,
                        "counterexample_residue": result.counterexample_residue or "",
                        "reason": result.reason,
                    }
                )
            if result.status == "vacuous":
                negative_label = "; ".join(rule_label(rule) for rule in negatives)
                rows.append(
                    {
                        "focus_r": focus_r,
                        "base_modulus": base.base_modulus,
                        "base_residue": base.base_residue,
                        "depth": depth,
                        "negative_rules": negative_label,
                        "target_rule": rule_label(target),
                        "status": result.status,
                        "verified_modulus": result.verified_modulus,
                        "refinement_ratio": result.refinement_ratio,
                        "antecedent_count": result.antecedent_count,
                        "counterexample_residue": result.counterexample_residue or "",
                        "reason": result.reason,
                    }
                )
                break

    summary = {
        "focus_r": focus_r,
        "remainders_sampled": len(remainders),
        "processed": processed,
        "no_candidate": no_candidate,
        "forced_implications_found": len(rows),
        "status_counts": status_counts.most_common(),
        "top_implication_patterns": implication_counts.most_common(10),
    }
    return rows, attempt_rows, summary


def write_markdown(summaries: list[dict[str, object]], rows: list[dict[str, object]], sampled: bool) -> None:
    top_patterns = Counter((row["negative_rules"], row["target_rule"]) for row in rows)
    lines = [
        "# Family Negative-Condition Implication Report",
        "",
        "This report searches for local implications of the form:",
        "",
        "```text",
        "Base AND NOT(A) => B",
        "Base AND NOT(A) AND NOT(B) => C",
        "```",
        "",
        "where `A`, `B`, and `C` are prime-factor family conditions. The checks",
        "are finite residue tests modulo the relevant lcm, capped by a refinement",
        "ratio. This is not a proof of the full Erdős-Straus conjecture.",
        "",
        f"Sampled analysis only: `{'yes' if sampled else 'no'}`.",
        "",
        "## Focus Summaries",
        "",
    ]
    for summary in summaries:
        lines.extend(
            [
                f"### focus {summary['focus_r']}",
                "",
                f"- remainders sampled: `{summary['remainders_sampled']}`",
                f"- forced implications found: `{summary['forced_implications_found']}`",
                f"- no-candidate classes: `{summary['no_candidate']}`",
                f"- status counts: `{summary['status_counts']}`",
                f"- top implication patterns: `{summary['top_implication_patterns']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Top Candidate Lemma Patterns",
            "",
        ]
    )
    if not top_patterns:
        lines.append("No strong negative-condition forcing pattern was found at this stage.")
        lines.append("")
    else:
        for (negative, target), count in top_patterns.most_common(20):
            lines.extend(
                [
                    f"### Pattern count `{count}`",
                    "",
                    "Claim shape:",
                    "",
                    "```text",
                    f"Base AND NOT({negative}) => {target}",
                    "```",
                    "",
                    "Status: computationally verified for the listed finite base classes;",
                    "not yet a general theorem.",
                    "",
                ]
            )

    lines.extend(
        [
            "## Verdict",
            "",
            "These are local symbolic implication candidates only. Unknown-large-ratio",
            "cases and failed implications are not hidden; they remain outside any",
            "candidate lemma.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path("family_negative_implication_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus-residue", type=int, choices=FOCUS_RESIDUES)
    parser.add_argument("--max-family-rules", type=int, default=30)
    parser.add_argument("--candidate-limit", type=int, default=8)
    parser.add_argument("--sample-limit", type=int, default=2000)
    parser.add_argument("--max-ratio", type=int, default=50_000)
    parser.add_argument("--search-depth", type=int, default=6)
    args = parser.parse_args()

    focus_residues = [args.focus_residue] if args.focus_residue else FOCUS_RESIDUES
    rules = load_family_rules(args.max_family_rules)

    all_rows: list[dict[str, object]] = []
    all_attempt_rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for focus_r in focus_residues:
        rows, attempt_rows, summary = analyze_focus(
            focus_r,
            rules,
            sample_limit=args.sample_limit,
            max_ratio=args.max_ratio,
            candidate_limit=args.candidate_limit,
            search_depth=args.search_depth,
        )
        all_rows.extend(rows)
        all_attempt_rows.extend(attempt_rows)
        summaries.append(summary)

    write_csv(
        Path("family_negative_implications.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "depth",
            "negative_rules",
            "target_rule",
            "status",
            "verified_modulus",
            "refinement_ratio",
            "antecedent_count",
            "counterexample_residue",
            "reason",
        ],
        all_rows,
    )
    write_csv(
        Path("family_negative_implication_attempts.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "depth",
            "negative_rules",
            "target_rule",
            "status",
            "verified_modulus",
            "refinement_ratio",
            "antecedent_count",
            "counterexample_residue",
            "reason",
        ],
        all_attempt_rows,
    )
    write_csv(
        Path("family_negative_implication_summary.csv"),
        [
            "focus_r",
            "remainders_sampled",
            "processed",
            "no_candidate",
            "forced_implications_found",
            "status_counts",
            "top_implication_patterns",
        ],
        summaries,
    )
    write_markdown(summaries, all_rows, sampled=True)

    print(f"Family rules loaded: {len(rules)}")
    print(f"Focus residues: {focus_residues}")
    print(f"Remainders sampled per focus: {args.sample_limit}")
    print(f"Forced implications found: {len(all_rows)}")
    for summary in summaries:
        print(
            f"focus {summary['focus_r']}: forced={summary['forced_implications_found']} "
            f"statuses={summary['status_counts']}"
        )
    print("Verdict: not proved yet")


if __name__ == "__main__":
    main()
