#!/usr/bin/env python3
"""Recursive lift-cover search for the previously uncovered 120120-core.

This script is an exploratory tool. It tries to cover classes

    n == residue mod modulus

by recursively lifting them to finer moduli and applying general-key rules.
It never writes a proof certificate for the full Erdos-Straus conjecture.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from attack_1_mod_24 import DEFAULT_GLOBAL_MODULUS
from erdos_straus import check_solution, first_compatible_d


BASE_MODULUS = DEFAULT_GLOBAL_MODULUS
UNCOVERED_PATH = Path(f"uncovered_1_mod_24_global_{BASE_MODULUS}.csv")
COMMON_D_VALUES = [3, 7, 11, 15, 19, 23, 31, 35, 39, 47, 71, 95, 119]


@dataclass(frozen=True)
class Rule:
    d: int
    a: int
    b: int

    @property
    def rule_modulus(self) -> int:
        return lcm_many(4, self.a, self.b)


@dataclass
class CandidateRule:
    rule: Rule
    sample_successes: int
    individual_coverage: int = 0
    individual_subresidues: int = 0


@dataclass
class ClassRecord:
    class_id: int
    parent_id: int | None
    root_id: int
    depth: int
    modulus: int
    residue: int
    status: str = "unresolved"
    covered_by: Rule | None = None
    reason: str = ""
    is_leaf: bool = True


@dataclass
class RuleRecord:
    class_id: int
    modulus: int
    residue: int
    rule: Rule
    covered_subclasses: int


def lcm_many(*values: int) -> int:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
    return result


def load_uncovered() -> list[int]:
    if not UNCOVERED_PATH.exists():
        raise FileNotFoundError(
            f"{UNCOVERED_PATH} not found. Run attack_1_mod_24.py --greedy-cover first."
        )

    residues: list[int] = []
    with UNCOVERED_PATH.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            modulus = int(row["modulus"])
            if modulus != BASE_MODULUS:
                raise ValueError(f"unexpected modulus {modulus}; expected {BASE_MODULUS}")
            residues.append(int(row["residue"]))
    return residues


def solution_from_rule(n: int, rule: Rule) -> tuple[int, int, int] | None:
    if (n + rule.d) % 4 != 0:
        return None
    product = n * (n + rule.d)
    if product % rule.a != 0 or product % rule.b != 0:
        return None
    return (n + rule.d) // 4, product // rule.a, product // rule.b


def rule_applies_to_n(n: int, rule: Rule) -> bool:
    return solution_from_rule(n, rule) is not None


def rule_covers_class(modulus: int, residue: int, rule: Rule) -> bool:
    if modulus % rule.rule_modulus != 0:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def find_minimal_rule(n: int, max_d: int) -> Rule | None:
    for d in range(first_compatible_d(n), max_d + 1, 4):
        product = n * (n + d)
        pair_sum = 4 * d
        for a in range(1, pair_sum // 2 + 1):
            b = pair_sum - a
            if product % a == 0 and product % b == 0:
                return Rule(d, a, b)
    return None


def cached_minimal_rule(
    n: int,
    max_d: int,
    cache: dict[tuple[int, int], Rule | None],
) -> Rule | None:
    key = (n, max_d)
    if key not in cache:
        cache[key] = find_minimal_rule(n, max_d)
    return cache[key]


def sample_values(modulus: int, residue: int) -> list[int]:
    samples: list[int] = []
    n = residue if residue > 1 else residue + modulus
    for offset in range(4):
        value = n + offset * modulus
        if value > 1:
            samples.append(value)
    return samples


def pairs_working_on_samples(d: int, samples: list[int], max_pairs: int) -> list[Rule]:
    """Generate rules for a d, keeping pairs that work on at least one sample."""
    if d <= 0:
        return []
    pair_sum = 4 * d
    rules: list[Rule] = []
    seen: set[tuple[int, int, int]] = set()
    products = [n * (n + d) for n in samples if (n + d) % 4 == 0]

    for a in range(1, pair_sum // 2 + 1):
        b = pair_sum - a
        for product in products:
            if product % a == 0 and product % b == 0:
                key = (d, a, b)
                if key not in seen:
                    seen.add(key)
                    rules.append(Rule(d, a, b))
                    if len(rules) >= max_pairs:
                        return rules
                break
    return rules


def candidate_rules_for_class(
    record: ClassRecord,
    args: argparse.Namespace,
    sample_cache: dict[tuple[int, int], Rule | None],
) -> list[CandidateRule]:
    samples = sample_values(record.modulus, record.residue)
    rules: dict[Rule, int] = {}
    d_values: set[int] = set(COMMON_D_VALUES)

    for sample in samples:
        sample_rule = cached_minimal_rule(sample, args.max_d, sample_cache)
        if sample_rule is None:
            continue
        rules[sample_rule] = rules.get(sample_rule, 0) + 1
        d_values.add(sample_rule.d)
        for delta in (-8, -4, 4, 8):
            nearby = sample_rule.d + delta
            if nearby > 0:
                d_values.add(nearby)

    compatible_d_values = sorted(
        d
        for d in d_values
        if d <= args.max_d and (record.residue + d) % 4 == 0
    )

    # Pair generation is deliberately sample-based. Exhaustive pair scans for
    # every recursive node are too expensive and too noisy for this stage.
    max_pairs_per_d = max(4, args.max_rule_candidates // max(1, len(compatible_d_values)))
    for d in compatible_d_values:
        for rule in pairs_working_on_samples(d, samples, max_pairs_per_d):
            score = sum(1 for sample in samples if rule_applies_to_n(sample, rule))
            if score:
                rules[rule] = max(rules.get(rule, 0), score)

    candidates = [CandidateRule(rule=rule, sample_successes=score) for rule, score in rules.items()]
    candidates.sort(
        key=lambda item: (
            -item.sample_successes,
            item.rule.rule_modulus,
            item.rule.d,
            item.rule.a,
            item.rule.b,
        )
    )
    return candidates[: args.max_rule_candidates]


def subresidues(modulus: int, residue: int, refined_modulus: int) -> list[int]:
    if refined_modulus % modulus != 0:
        raise ValueError("refined modulus must be a multiple of the current modulus")
    return [residue + k * modulus for k in range(refined_modulus // modulus)]


def coverage_count(modulus: int, residue: int, refined_modulus: int, rule: Rule) -> int:
    count = 0
    for subresidue in subresidues(modulus, residue, refined_modulus):
        if rule_covers_class(refined_modulus, subresidue, rule):
            count += 1
    return count


def rank_candidates_for_lift(
    record: ClassRecord,
    candidates: list[CandidateRule],
    args: argparse.Namespace,
) -> list[CandidateRule]:
    ranked: list[CandidateRule] = []
    for candidate in candidates:
        rule = candidate.rule
        refined_modulus = lcm_many(record.modulus, rule.rule_modulus)
        if refined_modulus == record.modulus:
            continue
        if refined_modulus > args.max_modulus:
            continue
        sub_count = refined_modulus // record.modulus
        if sub_count > args.max_subresidues_per_node:
            continue
        candidate.individual_subresidues = sub_count
        candidate.individual_coverage = coverage_count(
            record.modulus,
            record.residue,
            refined_modulus,
            rule,
        )
        if candidate.individual_coverage:
            ranked.append(candidate)

    ranked.sort(
        key=lambda item: (
            -item.individual_coverage,
            -item.sample_successes,
            item.individual_subresidues,
            item.rule.rule_modulus,
            item.rule.d,
        )
    )
    return ranked


def explain_lift_failure(
    record: ClassRecord,
    candidates: list[CandidateRule],
    args: argparse.Namespace,
) -> str:
    counts = Counter()
    for candidate in candidates:
        rule = candidate.rule
        refined_modulus = lcm_many(record.modulus, rule.rule_modulus)
        if refined_modulus == record.modulus:
            counts["no_new_modulus"] += 1
            continue
        if refined_modulus > args.max_modulus:
            counts["max_modulus_reached"] += 1
            continue
        sub_count = refined_modulus // record.modulus
        if sub_count > args.max_subresidues_per_node:
            counts["too_many_subresidues"] += 1
            continue
        covered = coverage_count(record.modulus, record.residue, refined_modulus, rule)
        if covered:
            counts["unexpected_rank_gap"] += 1
        else:
            counts["rule_only_covers_other_subclasses"] += 1

    if not counts:
        return "no_candidate_rules"
    reason, count = counts.most_common(1)[0]
    detail = ",".join(f"{name}={value}" for name, value in counts.most_common())
    return f"{reason} ({detail})"


def choose_refined_modulus(
    record: ClassRecord,
    ranked: list[CandidateRule],
    args: argparse.Namespace,
) -> tuple[int, list[Rule]]:
    refined_modulus = record.modulus
    chosen: list[Rule] = []

    for candidate in ranked:
        rule = candidate.rule
        next_modulus = lcm_many(refined_modulus, rule.rule_modulus)
        if next_modulus == refined_modulus:
            chosen.append(rule)
            continue
        if next_modulus > args.max_modulus:
            continue
        if next_modulus // record.modulus > args.max_subresidues_per_node:
            continue
        refined_modulus = next_modulus
        chosen.append(rule)
        if len(chosen) >= args.max_rule_candidates:
            break

    return refined_modulus, chosen


def greedy_cover_subresidues(
    record: ClassRecord,
    refined_modulus: int,
    rules: list[Rule],
) -> tuple[list[tuple[Rule, set[int]]], set[int]]:
    targets = set(subresidues(record.modulus, record.residue, refined_modulus))
    rule_cover: dict[Rule, set[int]] = {}
    for rule in rules:
        covered = {
            subresidue
            for subresidue in targets
            if rule_covers_class(refined_modulus, subresidue, rule)
        }
        if covered:
            rule_cover[rule] = covered

    selected: list[tuple[Rule, set[int]]] = []
    uncovered = set(targets)
    while uncovered:
        best_rule: Rule | None = None
        best_new: set[int] = set()
        for rule, covered in rule_cover.items():
            new = covered & uncovered
            if len(new) > len(best_new):
                best_rule = rule
                best_new = new
        if best_rule is None or not best_new:
            break
        selected.append((best_rule, set(best_new)))
        uncovered -= best_new

    return selected, uncovered


def make_record(
    records: dict[int, ClassRecord],
    next_id: int,
    parent: ClassRecord | None,
    depth: int,
    modulus: int,
    residue: int,
) -> ClassRecord:
    root_id = next_id if parent is None else parent.root_id
    record = ClassRecord(
        class_id=next_id,
        parent_id=None if parent is None else parent.class_id,
        root_id=root_id,
        depth=depth,
        modulus=modulus,
        residue=residue % modulus,
    )
    records[next_id] = record
    return record


def queue_item(
    record: ClassRecord,
    priority_score: int,
    strategy: str,
) -> tuple[int, int, int, int]:
    if strategy == "depth-first":
        return (-record.depth, record.modulus, -priority_score, record.class_id)
    return (record.depth, record.modulus, -priority_score, record.class_id)


def validate_covered_records(records: dict[int, ClassRecord]) -> list[str]:
    failures: list[str] = []
    for record in records.values():
        if record.status != "covered" or record.covered_by is None:
            continue
        rule = record.covered_by
        checked = 0
        for offset in range(3):
            n = record.residue + offset * record.modulus
            if n <= 1:
                continue
            solution = solution_from_rule(n, rule)
            if solution is None:
                record.status = "failed_validation"
                failures.append(
                    f"class_id={record.class_id}: rule divisibility failed for n={n}"
                )
                continue
            if not check_solution(n, *solution):
                record.status = "failed_validation"
                failures.append(
                    f"class_id={record.class_id}: check_solution failed for n={n}"
                )
            checked += 1
        if checked == 0:
            record.status = "failed_validation"
            failures.append(f"class_id={record.class_id}: no valid sample n checked")
    return failures


def output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.focus_residue is not None:
        prefix = f"recursive_focus_{args.focus_residue}"
        return (
            Path(f"{prefix}_classes.csv"),
            Path(f"{prefix}_rules.csv"),
            Path(f"{prefix}_unresolved.csv"),
        )
    return (
        Path("recursive_core_cover_classes.csv"),
        Path("recursive_core_cover_rules.csv"),
        Path("recursive_core_unresolved.csv"),
    )


def write_outputs(
    records: dict[int, ClassRecord],
    rule_records: list[RuleRecord],
    args: argparse.Namespace,
) -> tuple[Path, Path, Path]:
    classes_path, rules_path, unresolved_path = output_paths(args)

    with classes_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "class_id",
                "parent_id",
                "depth",
                "modulus",
                "residue",
                "status",
                "covered_by_d",
                "covered_by_a",
                "covered_by_b",
            ],
        )
        writer.writeheader()
        for class_id in sorted(records):
            record = records[class_id]
            rule = record.covered_by
            writer.writerow(
                {
                    "class_id": record.class_id,
                    "parent_id": "" if record.parent_id is None else record.parent_id,
                    "depth": record.depth,
                    "modulus": record.modulus,
                    "residue": record.residue,
                    "status": record.status,
                    "covered_by_d": "" if rule is None else rule.d,
                    "covered_by_a": "" if rule is None else rule.a,
                    "covered_by_b": "" if rule is None else rule.b,
                }
            )

    with rules_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "class_id",
                "modulus",
                "residue",
                "d",
                "a",
                "b",
                "rule_modulus",
                "covered_subclasses",
            ],
        )
        writer.writeheader()
        for item in rule_records:
            writer.writerow(
                {
                    "class_id": item.class_id,
                    "modulus": item.modulus,
                    "residue": item.residue,
                    "d": item.rule.d,
                    "a": item.rule.a,
                    "b": item.rule.b,
                    "rule_modulus": item.rule.rule_modulus,
                    "covered_subclasses": item.covered_subclasses,
                }
            )

    with unresolved_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["class_id", "depth", "modulus", "residue", "reason"],
        )
        writer.writeheader()
        for record in sorted(records.values(), key=lambda item: item.class_id):
            if record.is_leaf and record.status != "covered":
                writer.writerow(
                    {
                        "class_id": record.class_id,
                        "depth": record.depth,
                        "modulus": record.modulus,
                        "residue": record.residue,
                        "reason": record.reason or record.status,
                    }
                )
    return classes_path, rules_path, unresolved_path


def write_candidate_file(
    records: dict[int, ClassRecord],
    rule_records: list[RuleRecord],
    args: argparse.Namespace,
) -> Path:
    if args.focus_residue is not None:
        path = Path(f"candidate_focus_cover_{args.focus_residue}.md")
        title = f"# Candidate Focus Cover For Residue {args.focus_residue}"
        scope = (
            "It is a computer-found candidate local cover for one residue class "
            f"`n == {args.focus_residue} mod {BASE_MODULUS}`."
        )
    else:
        path = Path("candidate_recursive_cover_1_mod_24_core.md")
        title = "# Candidate Recursive Cover For The Previously Uncovered Core"
        scope = (
            "It is a computer-found candidate recursive cover for the previously\n"
            "uncovered n == 1 mod 24 core modulo 120120."
        )
    lines = [
        title,
        "",
        "This is NOT a proof of the full Erdos-Straus conjecture.",
        "",
        scope,
        "",
        "It needs independent mathematical verification.",
        "",
        "## Selected Rules",
        "",
        "| class_id | modulus | residue | d | a | b | rule_modulus | covered_subclasses |",
        "| - | - | - | - | - | - | - | - |",
    ]
    for item in rule_records:
        lines.append(
            f"| {item.class_id} | {item.modulus} | {item.residue} | "
            f"{item.rule.d} | {item.rule.a} | {item.rule.b} | "
            f"{item.rule.rule_modulus} | {item.covered_subclasses} |"
        )
    lines += [
        "",
        "## Covered Terminal Classes",
        "",
        "| class_id | parent_id | depth | modulus | residue | d | a | b |",
        "| - | - | - | - | - | - | - | - |",
    ]
    for record in sorted(records.values(), key=lambda item: item.class_id):
        if record.is_leaf and record.status == "covered" and record.covered_by is not None:
            rule = record.covered_by
            parent = "" if record.parent_id is None else record.parent_id
            lines.append(
                f"| {record.class_id} | {parent} | {record.depth} | {record.modulus} | "
                f"{record.residue} | {rule.d} | {rule.a} | {rule.b} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def process_cover(args: argparse.Namespace) -> dict[str, object]:
    residues = load_uncovered()
    if args.focus_residue is not None:
        if args.focus_residue not in residues:
            raise ValueError(
                f"focus residue {args.focus_residue} is not in {UNCOVERED_PATH}"
            )
        residues = [args.focus_residue]

    records: dict[int, ClassRecord] = {}
    rule_records: list[RuleRecord] = []
    sample_cache: dict[tuple[int, int], Rule | None] = {}
    heap: list[tuple[int, int, int, int]] = []
    next_id = 1

    for residue in residues:
        record = make_record(records, next_id, None, 0, BASE_MODULUS, residue)
        heapq.heappush(heap, queue_item(record, 0, args.strategy))
        next_id += 1

    processed = 0
    stopped_by_limit = False

    while heap:
        _, _, _, class_id = heapq.heappop(heap)
        record = records[class_id]
        if not record.is_leaf or record.status != "unresolved":
            continue

        processed += 1
        if args.progress_interval and processed % args.progress_interval == 0:
            leaf_unresolved = sum(
                1 for item in records.values() if item.is_leaf and item.status != "covered"
            )
            print(
                f"processed={processed} classes={len(records)} queue={len(heap)} "
                f"leaf_unresolved={leaf_unresolved} depth={record.depth} modulus={record.modulus}"
            )

        candidates = candidate_rules_for_class(record, args, sample_cache)
        full_rules = [
            candidate.rule
            for candidate in candidates
            if rule_covers_class(record.modulus, record.residue, candidate.rule)
        ]
        if full_rules:
            rule = min(full_rules, key=lambda item: (item.d, item.rule_modulus, item.a, item.b))
            record.status = "covered"
            record.covered_by = rule
            record.reason = "covered_by_full_class_rule"
            continue

        if record.depth >= args.max_depth:
            record.status = "limit_hit"
            record.reason = "max_depth"
            continue

        if not candidates:
            record.status = "unresolved"
            record.reason = "no_candidate_rules"
            continue

        ranked = rank_candidates_for_lift(record, candidates, args)
        if not ranked:
            record.status = "limit_hit"
            record.reason = explain_lift_failure(record, candidates, args)
            continue

        refined_modulus, chosen_rules = choose_refined_modulus(record, ranked, args)
        if refined_modulus == record.modulus or not chosen_rules:
            record.status = "unresolved"
            record.reason = "no_refinement_progress"
            continue

        selected, uncovered = greedy_cover_subresidues(record, refined_modulus, chosen_rules)
        if not selected:
            record.status = "unresolved"
            record.reason = "lift_created_no_covered_subclasses"
            continue

        subresidue_count = refined_modulus // record.modulus
        if len(records) + subresidue_count > args.max_classes:
            record.status = "limit_hit"
            record.reason = "max_classes"
            stopped_by_limit = True
            break

        record.is_leaf = False
        record.reason = f"expanded_to_modulus_{refined_modulus}"
        covered_subresidues: dict[int, Rule] = {}
        for rule, covered in selected:
            rule_records.append(
                RuleRecord(
                    class_id=record.class_id,
                    modulus=record.modulus,
                    residue=record.residue,
                    rule=rule,
                    covered_subclasses=len(covered),
                )
            )
            for subresidue in covered:
                covered_subresidues[subresidue] = rule

        priority_score = max((candidate.sample_successes for candidate in ranked), default=0)
        for subresidue in subresidues(record.modulus, record.residue, refined_modulus):
            child = make_record(
                records,
                next_id,
                record,
                record.depth + 1,
                refined_modulus,
                subresidue,
            )
            next_id += 1
            if subresidue in covered_subresidues:
                child.status = "covered"
                child.covered_by = covered_subresidues[subresidue]
                child.reason = "covered_by_lift_rule"
            elif subresidue in uncovered:
                heapq.heappush(heap, queue_item(child, priority_score, args.strategy))
            else:
                # This should not happen, but keeping it explicit protects the
                # accounting from silently dropping a subresidue.
                child.status = "unresolved"
                child.reason = "subresidue_accounting_gap"
                heapq.heappush(heap, queue_item(child, 0, args.strategy))

        if stopped_by_limit:
            break

    if stopped_by_limit:
        for _, _, _, queued_class_id in heap:
            queued = records[queued_class_id]
            if queued.is_leaf and queued.status == "unresolved" and not queued.reason:
                queued.reason = "not_processed_due_to_global_limit"

    validation_failures = validate_covered_records(records)
    classes_path, rules_path, unresolved_path = write_outputs(records, rule_records, args)

    leaf_records = [record for record in records.values() if record.is_leaf]
    leaf_unresolved = [record for record in leaf_records if record.status != "covered"]
    roots_by_id = {record.class_id: record for record in records.values() if record.parent_id is None}
    leaf_status_by_root: dict[int, list[ClassRecord]] = defaultdict(list)
    for record in leaf_records:
        leaf_status_by_root[record.root_id].append(record)

    covered_initial = [
        roots_by_id[root_id].residue
        for root_id, leaves in leaf_status_by_root.items()
        if leaves and all(leaf.status == "covered" for leaf in leaves)
    ]
    unresolved_initial = [
        roots_by_id[root_id].residue
        for root_id, leaves in leaf_status_by_root.items()
        if not leaves or any(leaf.status != "covered" for leaf in leaves)
    ]

    candidate_path: Path | None = None
    if not leaf_unresolved and not validation_failures and len(covered_initial) == len(residues):
        candidate_path = write_candidate_file(records, rule_records, args)

    covered_rules = [record.covered_by for record in leaf_records if record.covered_by is not None]
    d_counts = Counter(rule.d for rule in covered_rules)
    pair_counts = Counter((rule.a, rule.b) for rule in covered_rules)

    return {
        "initial_count": len(residues),
        "covered_initial": covered_initial,
        "unresolved_initial": unresolved_initial,
        "total_covered_classes": sum(1 for record in leaf_records if record.status == "covered"),
        "total_unresolved_classes": len(leaf_unresolved),
        "max_depth": max((record.depth for record in records.values()), default=0),
        "max_modulus": max((record.modulus for record in records.values()), default=BASE_MODULUS),
        "validation_failures": validation_failures,
        "candidate_path": candidate_path,
        "d_counts": d_counts,
        "pair_counts": pair_counts,
        "stopped_by_limit": stopped_by_limit,
        "total_records": len(records),
        "rule_records": len(rule_records),
        "classes_path": classes_path,
        "rules_path": rules_path,
        "unresolved_path": unresolved_path,
        "focus_residue": args.focus_residue,
        "records": records,
        "sample_cache": sample_cache,
        "max_d": args.max_d,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recursive lift-cover search for the 330-core.")
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--max-d", type=int, default=10_000)
    parser.add_argument("--max-rule-candidates", type=int, default=200)
    parser.add_argument("--max-classes", type=int, default=200_000)
    parser.add_argument("--max-modulus", type=int, default=1_000_000_000_000)
    parser.add_argument("--max-subresidues-per-node", type=int, default=5_000)
    parser.add_argument("--progress-interval", type=int, default=500)
    parser.add_argument("--focus-residue", type=int)
    parser.add_argument(
        "--strategy",
        choices=["breadth-first", "depth-first"],
        default="breadth-first",
    )
    return parser.parse_args()


def sample_rule_summary(
    record: ClassRecord,
    max_d: int,
    sample_cache: dict[tuple[int, int], Rule | None],
) -> str:
    parts: list[str] = []
    for sample in sample_values(record.modulus, record.residue):
        rule = cached_minimal_rule(sample, max_d, sample_cache)
        if rule is None:
            parts.append(f"{sample}: none")
        else:
            parts.append(
                f"{sample}: d={rule.d},a={rule.a},b={rule.b},rm={rule.rule_modulus}"
            )
    return "; ".join(parts)


def print_focus_unresolved_diagnostics(summary: dict[str, object]) -> None:
    records: dict[int, ClassRecord] = summary["records"]  # type: ignore[assignment]
    sample_cache: dict[tuple[int, int], Rule | None] = summary["sample_cache"]  # type: ignore[assignment]
    max_d: int = summary["max_d"]  # type: ignore[assignment]
    unresolved = [
        record
        for record in records.values()
        if record.is_leaf and record.status != "covered"
    ]
    unresolved.sort(key=lambda item: (-item.depth, item.modulus, item.class_id))

    if not unresolved:
        return

    print("first unresolved leaf classes:")
    for record in unresolved[:20]:
        reason = record.reason or record.status
        print(
            f"  class_id={record.class_id} depth={record.depth} "
            f"modulus={record.modulus} residue={record.residue} reason={reason}"
        )
        print(f"    samples: {sample_rule_summary(record, max_d, sample_cache)}")
    print()


def print_summary(summary: dict[str, object]) -> None:
    d_counts: Counter[int] = summary["d_counts"]  # type: ignore[assignment]
    pair_counts: Counter[tuple[int, int]] = summary["pair_counts"]  # type: ignore[assignment]
    validation_failures: list[str] = summary["validation_failures"]  # type: ignore[assignment]
    unresolved_initial: list[int] = summary["unresolved_initial"]  # type: ignore[assignment]
    candidate_path = summary["candidate_path"]
    focus_residue = summary["focus_residue"]

    print()
    print("summary:")
    if focus_residue is not None:
        root_covered = len(unresolved_initial) == 0
        print(f"  focus residue: {focus_residue}")
        print(f"  root covered fully: {'yes' if root_covered else 'no'}")
    else:
        print(f"  initial core residues: {summary['initial_count']}")
        print(f"  covered initial residues fully: {len(summary['covered_initial'])}")
        print(f"  unresolved initial residues: {len(unresolved_initial)}")
        print(f"  unresolved initial residue list: {unresolved_initial}")
    print(f"  total covered classes: {summary['total_covered_classes']}")
    print(f"  total unresolved classes: {summary['total_unresolved_classes']}")
    print(f"  total class records: {summary['total_records']}")
    print(f"  selected rule records: {summary['rule_records']}")
    print(f"  max depth reached: {summary['max_depth']}")
    print(f"  max modulus used: {summary['max_modulus']}")
    print(f"  stopped by limit: {summary['stopped_by_limit']}")
    print(f"  validation failures: {validation_failures[:20]}{' ...' if len(validation_failures) > 20 else ''}")
    print(f"  classes csv: {summary['classes_path']}")
    print(f"  rules csv: {summary['rules_path']}")
    print(f"  unresolved csv: {summary['unresolved_path']}")
    print()

    print("most common d:")
    for d, count in d_counts.most_common(20):
        print(f"  d={d}: {count}")
    print()

    print("most common pairs:")
    for pair, count in pair_counts.most_common(20):
        print(f"  {pair}: {count}")
    print()

    if focus_residue is not None and unresolved_initial:
        print_focus_unresolved_diagnostics(summary)

    if candidate_path is not None:
        print(f"candidate file created: {candidate_path}")
        if focus_residue is not None:
            print("verdict: focus residue covered")
        else:
            print("verdict: candidate recursive core cover generated")
    else:
        print("candidate file created: no")
        print("verdict: not proved yet")


def main() -> None:
    args = parse_args()
    summary = process_cover(args)
    print_summary(summary)


if __name__ == "__main__":
    main()
