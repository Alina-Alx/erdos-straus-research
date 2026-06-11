#!/usr/bin/env python3
"""Look for human-readable lemma candidates in remaining symbolic remainders.

This script is intentionally diagnostic. It does not build another cover tree
and it does not claim a proof of the Erdos-Straus conjecture.
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

from erdos_straus import check_solution, first_compatible_d


FOCUS_RESIDUES = [289, 361, 529, 841, 961]
SMALL_PRIMES = [5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
MOD_COLUMNS = [8, 12, 24, 60, 120, 840]
REMAINDER_PATHS = {
    focus_r: Path(f"symbolic_remainder_focus_{focus_r}_remaining.csv")
    for focus_r in FOCUS_RESIDUES
}
OPTIONAL_PATHS = [
    Path("symbolic_master_keys.csv"),
    Path("symbolic_rule_summary.csv"),
    Path("recursive_failure_diagnostics.csv"),
]
CONDITION_RE = re.compile(
    r"not\(n mod (?P<q>\d+) in "
    r"(?:\{(?P<brace_residues>[^}]*)\}|"
    r"S\[d=(?P<d>\d+),a=(?P<a>\d+),b=(?P<b>\d+),size=(?P<size>\d+)\])"
    r"\)"
)


@dataclass(frozen=True)
class RuleKey:
    d: int
    a: int
    b: int

    @property
    def q(self) -> int:
        return lcm_many(4, self.a, self.b)


@dataclass
class RemainderRow:
    focus_r: int
    base_modulus: int
    base_residue: int
    conditions_count: int
    condition_summary: str
    status: str
    visible_q_values: tuple[int, ...]
    visible_exclusions: dict[int, set[int]]
    truncated: bool

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.focus_r, self.base_modulus, self.base_residue)


@dataclass
class LemmaCandidate:
    lemma_id: int
    title: str
    claim: str
    d: int
    a: int
    b: int
    condition_type: str
    condition_modulus: int
    condition_residues: tuple[int, ...] = field(default_factory=tuple)
    condition_prime: int | None = None
    condition_qr: bool | None = None
    why: str = ""
    support_count: int = 0
    status: str = "conjectural"

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


def parse_int(value: str, default: int = 0) -> int:
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


def factor_text(value: int, max_factor_value: int = 10_000_000) -> str:
    if value <= 1:
        return str(value)
    if value > max_factor_value:
        return "too_large"
    factors = factorization(value)
    return "*".join(
        str(prime) if exponent == 1 else f"{prime}^{exponent}"
        for prime, exponent in factors
    )


def prime_factors(value: int) -> tuple[int, ...]:
    return tuple(prime for prime, _ in factorization(value))


def is_square_integer(value: int) -> bool:
    if value < 0:
        return False
    root = math.isqrt(value)
    return root * root == value


def quadratic_residues(prime: int) -> set[int]:
    return {(value * value) % prime for value in range(prime)}


QR_CACHE = {prime: quadratic_residues(prime) for prime in SMALL_PRIMES}


def parse_visible_conditions(summary: str) -> tuple[tuple[int, ...], dict[int, set[int]], bool]:
    q_values: list[int] = []
    exclusions: defaultdict[int, set[int]] = defaultdict(set)
    for match in CONDITION_RE.finditer(summary or ""):
        q = int(match.group("q"))
        q_values.append(q)
        residues_text = match.group("brace_residues")
        if residues_text is None:
            continue
        for part in residues_text.split(","):
            part = part.strip()
            if not part or part == "...":
                continue
            try:
                exclusions[q].add(int(part) % q)
            except ValueError:
                continue
    return tuple(q_values), dict(exclusions), "..." in (summary or "")


def capped_lcm(values: Iterable[int], cap: int) -> tuple[int | None, str]:
    result = 1
    for value in values:
        result = result * value // math.gcd(result, value)
        if result > cap:
            return None, f"exceeds_{cap}"
    return result, "ok"


def load_remainders(sample_limit: int) -> tuple[list[RemainderRow], list[Path]]:
    missing = [path for path in REMAINDER_PATHS.values() if not path.exists()]
    rows: list[RemainderRow] = []
    per_focus_limit = sample_limit // len(FOCUS_RESIDUES) if sample_limit else 0
    remainder_budget = sample_limit if sample_limit else None

    for focus_r, path in REMAINDER_PATHS.items():
        if not path.exists():
            continue
        raw_rows = read_csv_rows(path)
        if per_focus_limit:
            raw_rows = evenly_sample(raw_rows, per_focus_limit)
        for row in raw_rows:
            if remainder_budget is not None and len(rows) >= remainder_budget:
                break
            q_values, exclusions, truncated = parse_visible_conditions(row.get("condition_summary", ""))
            rows.append(
                RemainderRow(
                    focus_r=focus_r,
                    base_modulus=int(row["base_modulus"]),
                    base_residue=int(row["base_residue"]),
                    conditions_count=int(row["conditions_count"]),
                    condition_summary=row.get("condition_summary", ""),
                    status=row.get("status", ""),
                    visible_q_values=q_values,
                    visible_exclusions=exclusions,
                    truncated=truncated,
                )
            )
    return rows, missing


def evenly_sample(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if limit <= 0 or len(rows) <= limit:
        return rows
    if limit == 1:
        return [rows[0]]
    step = (len(rows) - 1) / (limit - 1)
    return [rows[round(index * step)] for index in range(limit)]


def feature_names_for_row(row: RemainderRow) -> set[str]:
    r = row.base_residue
    m = row.base_modulus
    features = {
        f"focus={row.focus_r}",
        f"gcd_r_m={math.gcd(r, m)}",
        f"gcd_r_m_is_1={math.gcd(r, m) == 1}",
        f"is_integer_square={is_square_integer(r)}",
        f"condition_summary_truncated={row.truncated}",
    }
    for modulus in MOD_COLUMNS:
        features.add(f"r_mod_{modulus}={r % modulus}")
    for prime in SMALL_PRIMES:
        features.add(f"r_mod_{prime}={r % prime}")
        features.add(f"r_qr_mod_{prime}={r % prime in QR_CACHE[prime]}")
    q_factor_primes = set()
    for q in row.visible_q_values:
        for prime in prime_factors(q):
            q_factor_primes.add(prime)
    for prime in sorted(q_factor_primes):
        features.add(f"visible_q_has_factor_{prime}=True")
    return features


def features_csv_rows(rows: list[RemainderRow]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        r = row.base_residue
        m = row.base_modulus
        gcd_value = math.gcd(r, m)
        q_lcm, q_lcm_status = capped_lcm(row.visible_q_values, 10**18)
        q_factors = sorted({prime for q in row.visible_q_values for prime in prime_factors(q)})
        out: dict[str, object] = {
            "focus_r": row.focus_r,
            "base_modulus": m,
            "base_residue": r,
            "number_of_excluded_conditions": row.conditions_count,
            "visible_excluded_conditions": len(row.visible_q_values),
            "condition_summary_truncated": row.truncated,
            "visible_q_values": ";".join(str(q) for q in row.visible_q_values),
            "visible_q_lcm": "" if q_lcm is None else q_lcm,
            "visible_q_lcm_status": q_lcm_status,
            "visible_q_prime_factors": ";".join(str(prime) for prime in q_factors),
            "gcd_r_m": gcd_value,
            "gcd_r_m_factorization": factor_text(gcd_value),
            "r_factorization_if_small": factor_text(r),
            "is_integer_square": is_square_integer(r),
        }
        for modulus in MOD_COLUMNS:
            out[f"r_mod_{modulus}"] = r % modulus
        for prime in SMALL_PRIMES:
            out[f"r_mod_{prime}"] = r % prime
            out[f"is_quadratic_residue_mod_{prime}"] = r % prime in QR_CACHE[prime]
        output.append(out)
    return output


def load_diagnostics_rows() -> list[dict[str, str]]:
    path = Path("recursive_failure_diagnostics.csv")
    return read_csv_rows(path) if path.exists() else []


def diagnostics_feature_names(row: dict[str, str]) -> set[str]:
    focus_r = int(row["focus_r"])
    r = int(row["residue"])
    m = int(row["modulus"])
    synthetic = RemainderRow(
        focus_r=focus_r,
        base_modulus=m,
        base_residue=r,
        conditions_count=0,
        condition_summary="",
        status="diagnostic",
        visible_q_values=(),
        visible_exclusions={},
        truncated=False,
    )
    return {
        feature
        for feature in feature_names_for_row(synthetic)
        if not feature.startswith("visible_q_has_factor_")
        and not feature.startswith("condition_summary_truncated=")
    }


def comparison_rows(
    remaining: list[RemainderRow],
    diagnostics_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    remaining_keys = {row.key for row in remaining}
    remaining_counter: Counter[str] = Counter()
    covered_counter: Counter[str] = Counter()
    for row in remaining:
        remaining_counter.update(
            comparable_feature
            for comparable_feature in feature_names_for_row(row)
            if not comparable_feature.startswith("visible_q_has_factor_")
            and not comparable_feature.startswith("condition_summary_truncated=")
        )

    for row in diagnostics_rows:
        key = (int(row["focus_r"]), int(row["modulus"]), int(row["residue"]))
        if key in remaining_keys:
            continue
        covered_counter.update(diagnostics_feature_names(row))

    total_remaining = max(len(remaining), 1)
    total_covered = max(len(diagnostics_rows) - len(remaining_keys), 1)
    rows: list[dict[str, object]] = []
    for feature in sorted(set(remaining_counter) | set(covered_counter)):
        remaining_count = remaining_counter[feature]
        covered_count = covered_counter[feature]
        if covered_count == 0:
            enrichment = "inf" if remaining_count else "0"
        else:
            enrichment = (remaining_count / total_remaining) / (covered_count / total_covered)
        rows.append(
            {
                "feature": feature,
                "remaining_count": remaining_count,
                "covered_count": covered_count,
                "enrichment_ratio": enrichment,
            }
        )
    rows.sort(
        key=lambda row: (
            float("inf") if row["enrichment_ratio"] == "inf" else float(row["enrichment_ratio"]),
            int(row["remaining_count"]),
        ),
        reverse=True,
    )
    return rows


def load_rule_residue_sets() -> dict[RuleKey, set[int]]:
    path = Path("symbolic_rule_residue_sets.csv")
    if not path.exists():
        return {}
    grouped: defaultdict[RuleKey, set[int]] = defaultdict(set)
    for row in read_csv_rows(path):
        key = RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        grouped[key].add(int(row["residue_t"]) % key.q)
    return dict(grouped)


def rule_covers_residue(rule: RuleKey, residue: int) -> bool:
    if rule.a + rule.b != 4 * rule.d:
        return False
    if (residue + rule.d) % 4 != 0:
        return False
    product = residue * (residue + rule.d)
    return product % rule.a == 0 and product % rule.b == 0


def build_rule_residue_set(rule: RuleKey, max_q: int) -> set[int] | None:
    if rule.q > max_q:
        return None
    return {residue for residue in range(rule.q) if rule_covers_residue(rule, residue)}


def load_selected_rules() -> tuple[Counter[int], Counter[tuple[int, int]], Counter[RuleKey]]:
    d_counter: Counter[int] = Counter()
    pair_counter: Counter[tuple[int, int]] = Counter()
    rule_counter: Counter[RuleKey] = Counter()
    for focus_r in FOCUS_RESIDUES:
        for prefix in ("symbolic_remainder_focus", "symbolic_cover_focus"):
            path = Path(f"{prefix}_{focus_r}_selected_rules.csv")
            if not path.exists():
                continue
            for row in read_csv_rows(path):
                weight = (
                    parse_int(row.get("fully_covered_count", ""), 0)
                    or parse_int(row.get("classes_fully_covered", ""), 0)
                    or 1
                )
                d = int(row["d"])
                a = int(row["a"])
                b = int(row["b"])
                d_counter[d] += weight
                pair_counter[(a, b)] += weight
                rule_counter[RuleKey(d, a, b)] += weight
    return d_counter, pair_counter, rule_counter


def diagnostics_minimal_rule_map() -> dict[tuple[int, int, int], dict[str, str]]:
    rows = load_diagnostics_rows()
    return {
        (int(row["focus_r"]), int(row["modulus"]), int(row["residue"])): row
        for row in rows
    }


def minimal_general_key(n: int, max_d: int) -> tuple[int, int, int, int, int, int] | None:
    for d in range(first_compatible_d(n), max_d + 1, 4):
        product = n * (n + d)
        pair_sum = 4 * d
        for a in range(1, pair_sum // 2 + 1):
            b = pair_sum - a
            if product % a != 0 or product % b != 0:
                continue
            x = (n + d) // 4
            y = product // a
            z = product // b
            if check_solution(n, x, y, z):
                return (d, a, b, x, y, z)
    return None


def sample_remainders_by_focus(rows: list[RemainderRow], per_focus: int) -> list[RemainderRow]:
    sampled: list[RemainderRow] = []
    grouped: defaultdict[int, list[RemainderRow]] = defaultdict(list)
    for row in rows:
        grouped[row.focus_r].append(row)
    for focus_r in FOCUS_RESIDUES:
        focus_rows = grouped.get(focus_r, [])
        if len(focus_rows) <= per_focus:
            sampled.extend(focus_rows)
            continue
        step = (len(focus_rows) - 1) / (per_focus - 1)
        sampled.extend(focus_rows[round(index * step)] for index in range(per_focus))
    return sampled


def sample_minimal_rule_rows(
    remaining: list[RemainderRow],
    max_d: int,
    sample_per_focus: int,
) -> list[dict[str, object]]:
    diagnostic_map = diagnostics_minimal_rule_map()
    sampled = sample_remainders_by_focus(remaining, sample_per_focus)
    selected_rule_weights = load_selected_rules()[2]
    rows: list[dict[str, object]] = []

    for remainder in sampled:
        n = remainder.base_residue if remainder.base_residue > 1 else remainder.base_residue + remainder.base_modulus
        source = "computed"
        d = a = b = x = y = z = None
        diagnostic = diagnostic_map.get(remainder.key)
        if diagnostic and diagnostic.get("d"):
            d = int(diagnostic["d"])
            a = int(diagnostic["a"])
            b = int(diagnostic["b"])
            source = "recursive_failure_diagnostics"
            product = n * (n + d)
            x = (n + d) // 4
            y = product // a
            z = product // b
        else:
            solution = minimal_general_key(n, max_d)
            if solution:
                d, a, b, x, y, z = solution
        if d is None or a is None or b is None:
            rows.append(
                {
                    "focus_r": remainder.focus_r,
                    "base_modulus": remainder.base_modulus,
                    "base_residue": remainder.base_residue,
                    "sample_n": n,
                    "d": "",
                    "a": "",
                    "b": "",
                    "x": "",
                    "y": "",
                    "z": "",
                    "verified": False,
                    "rule_modulus": "",
                    "rule_prime_factors": "",
                    "sample_satisfies_visible_conditions": sample_satisfies_visible_conditions(n, remainder),
                    "source": source,
                    "why_not_closed_earlier": "no_rule_found_up_to_max_d",
                }
            )
            continue

        rule = RuleKey(d, a, b)
        verified = check_solution(n, int(x), int(y), int(z)) if x and y and z else False
        rows.append(
            {
                "focus_r": remainder.focus_r,
                "base_modulus": remainder.base_modulus,
                "base_residue": remainder.base_residue,
                "sample_n": n,
                "d": d,
                "a": a,
                "b": b,
                "x": x,
                "y": y,
                "z": z,
                "verified": verified,
                "rule_modulus": rule.q,
                "rule_prime_factors": ";".join(str(prime) for prime in prime_factors(rule.q)),
                "sample_satisfies_visible_conditions": sample_satisfies_visible_conditions(n, remainder),
                "source": source,
                "why_not_closed_earlier": why_not_closed_earlier(n, remainder, rule, selected_rule_weights),
            }
        )
    return rows


def sample_satisfies_visible_conditions(n: int, remainder: RemainderRow) -> bool:
    return all(n % q not in residues for q, residues in remainder.visible_exclusions.items())


def why_not_closed_earlier(
    n: int,
    remainder: RemainderRow,
    rule: RuleKey,
    selected_rule_weights: Counter[RuleKey],
) -> str:
    if rule.q in remainder.visible_exclusions:
        if n % rule.q in remainder.visible_exclusions[rule.q]:
            return "sample_rule_residue_is_visibly_excluded"
        return "same_rule_modulus_visible_but_only_partial_remainder"
    visible_factor_primes = {prime for q in remainder.visible_q_values for prime in prime_factors(q)}
    rule_factor_primes = set(prime_factors(rule.q))
    if rule_factor_primes & visible_factor_primes:
        return "shares_prime_factors_with_visible_exclusions_but_not_same_q"
    if selected_rule_weights[rule] == 0:
        return "rule_not_selected_by_symbolic_cover_or_remainder_greedy"
    return "selected_rule_only_partial_or_unknown_on_this_remainder"


def top_counter_text(counter: Counter[object], limit: int = 10) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{count}" for key, count in counter.most_common(limit))


def write_simple_patterns(
    remaining: list[RemainderRow],
    comparison: list[dict[str, object]],
    sample_rules: list[dict[str, object]],
) -> list[str]:
    lines = [
        "# Remaining Simple Patterns",
        "",
        "These are human-readable diagnostics, not proof claims.",
        "",
    ]
    total = len(remaining)
    q_factor_counter: Counter[int] = Counter()
    q_counter: Counter[int] = Counter()
    condition_counts = Counter(row.conditions_count for row in remaining)
    trunc_count = sum(row.truncated for row in remaining)
    gcd_counter = Counter(math.gcd(row.base_residue, row.base_modulus) for row in remaining)
    mod24_counter = Counter(row.base_residue % 24 for row in remaining)
    qr_counters = {
        prime: sum(row.base_residue % prime in QR_CACHE[prime] for row in remaining)
        for prime in SMALL_PRIMES
    }
    for row in remaining:
        q_counter.update(row.visible_q_values)
        for q in row.visible_q_values:
            q_factor_counter.update(prime_factors(q))

    lines.extend(
        [
            f"Total remaining remainders analyzed: `{total}`.",
            f"Condition summaries truncated: `{trunc_count}` "
            f"({trunc_count / total:.2%} of analyzed rows)." if total else "No rows.",
            f"Top reported condition counts: `{top_counter_text(condition_counts)}`.",
            f"Top gcd(r,m): `{top_counter_text(gcd_counter)}`.",
            f"r mod 24 distribution: `{top_counter_text(mod24_counter)}`.",
            f"Top visible excluded q values: `{top_counter_text(q_counter)}`.",
            f"Top visible q prime factors: `{top_counter_text(q_factor_counter)}`.",
            "",
            "## Quadratic-Residue Rates",
            "",
        ]
    )
    for prime, count in sorted(qr_counters.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- mod {prime}: {count}/{total} = {count / total:.2%}" if total else f"- mod {prime}: no rows")

    sample_d = Counter(int(row["d"]) for row in sample_rules if row["d"] != "")
    sample_pairs = Counter((int(row["a"]), int(row["b"])) for row in sample_rules if row["a"] != "")
    sample_q_factors: Counter[int] = Counter()
    for row in sample_rules:
        for part in str(row.get("rule_prime_factors", "")).split(";"):
            if part:
                sample_q_factors[int(part)] += 1

    lines.extend(
        [
            "",
            "## Sample Minimal Rules",
            "",
            f"Top minimal d: `{top_counter_text(sample_d)}`.",
            f"Top minimal pairs: `{top_counter_text(sample_pairs)}`.",
            f"Top sample rule-modulus prime factors: `{top_counter_text(sample_q_factors)}`.",
            "",
            "## Enriched Simple Features",
            "",
        ]
    )
    for row in comparison[:20]:
        lines.append(
            f"- `{row['feature']}`: remaining={row['remaining_count']}, "
            f"covered={row['covered_count']}, enrichment={row['enrichment_ratio']}"
        )

    lines.extend(
        [
            "",
            "## Short Read",
            "",
            "The remaining core is still dominated by residue-class structure and",
            "large stacks of visible q-exclusions. A clean one-prime separator did",
            "not emerge from this pass; candidate lemmas below test both fixed-rule",
            "residue sets and deliberately simpler conditions.",
        ]
    )
    Path("remaining_simple_patterns.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def generate_lemma_candidates(
    sample_rules: list[dict[str, object]],
    rule_sets: dict[RuleKey, set[int]],
    max_q: int,
) -> list[LemmaCandidate]:
    rule_counter = Counter(
        RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))
        for row in sample_rules
        if row["d"] != ""
    )
    candidates: list[LemmaCandidate] = []
    next_id = 1

    for rule, support in rule_counter.most_common(5):
        residues = rule_sets.get(rule) or build_rule_residue_set(rule, max_q) or set()
        if not residues:
            continue
        candidates.append(
            LemmaCandidate(
                lemma_id=next_id,
                title=f"Fixed residue-set rule d={rule.d}, pair=({rule.a},{rule.b})",
                claim=f"If n mod {rule.q} is in S_rule for d={rule.d}, a={rule.a}, b={rule.b}, then the rule covers n.",
                d=rule.d,
                a=rule.a,
                b=rule.b,
                condition_type="mod_in",
                condition_modulus=rule.q,
                condition_residues=tuple(sorted(residues)),
                why="For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.",
                support_count=support,
                status="proven algebraically if residue test passes",
            )
        )
        next_id += 1

    grouped_rows: defaultdict[RuleKey, list[dict[str, object]]] = defaultdict(list)
    for row in sample_rules:
        if row["d"] == "":
            continue
        grouped_rows[RuleKey(int(row["d"]), int(row["a"]), int(row["b"]))].append(row)

    for rule, rows in rule_counter.most_common(12):
        best: tuple[int, int, int] | None = None
        for prime in SMALL_PRIMES:
            counts = Counter(int(row["sample_n"]) % prime for row in grouped_rows[rule])
            residue, count = counts.most_common(1)[0]
            if count < 5:
                continue
            if best is None or count > best[2]:
                best = (prime, residue, count)
        if best is None:
            continue
        prime, residue, count = best
        candidates.append(
            LemmaCandidate(
                lemma_id=next_id,
                title=f"Simple congruence attempt for d={rule.d}, pair=({rule.a},{rule.b})",
                claim=f"If n == {residue} mod {prime}, then rule d={rule.d}, a={rule.a}, b={rule.b} covers n.",
                d=rule.d,
                a=rule.a,
                b=rule.b,
                condition_type="mod_eq",
                condition_modulus=prime,
                condition_residues=(residue,),
                condition_prime=prime,
                why="This congruence was frequent among sampled remaining rows using the same minimal rule.",
                support_count=count,
                status="conjectural before residue test",
            )
        )
        next_id += 1
        if len(candidates) >= 10:
            break
    return candidates


def candidate_condition_holds(candidate: LemmaCandidate, residue: int) -> bool:
    if candidate.condition_type == "mod_in":
        return residue % candidate.condition_modulus in set(candidate.condition_residues)
    if candidate.condition_type == "mod_eq":
        return residue % candidate.condition_modulus == candidate.condition_residues[0]
    if candidate.condition_type == "qr_mod" and candidate.condition_prime is not None:
        value = residue % candidate.condition_prime
        is_qr = value in QR_CACHE[candidate.condition_prime]
        return is_qr is bool(candidate.condition_qr)
    raise ValueError(f"unknown candidate condition type: {candidate.condition_type}")


def test_candidate(candidate: LemmaCandidate, max_test_L: int) -> dict[str, object]:
    L = lcm_many(4, candidate.a, candidate.b, candidate.condition_modulus)
    if L > max_test_L:
        return {
            "lemma_id": candidate.lemma_id,
            "d": candidate.d,
            "a": candidate.a,
            "b": candidate.b,
            "L": L,
            "tested_residues": "",
            "passed": False,
            "failed_residue": "",
            "status": "skipped_L_exceeds_limit",
        }
    tested = 0
    for residue in range(L):
        if not candidate_condition_holds(candidate, residue):
            continue
        tested += 1
        product = residue * (residue + candidate.d)
        if (
            (residue + candidate.d) % 4 != 0
            or product % candidate.a != 0
            or product % candidate.b != 0
        ):
            return {
                "lemma_id": candidate.lemma_id,
                "d": candidate.d,
                "a": candidate.a,
                "b": candidate.b,
                "L": L,
                "tested_residues": tested,
                "passed": False,
                "failed_residue": residue,
                "status": "failed_counterexample_residue",
            }
    return {
        "lemma_id": candidate.lemma_id,
        "d": candidate.d,
        "a": candidate.a,
        "b": candidate.b,
        "L": L,
        "tested_residues": tested,
        "passed": True,
        "failed_residue": "",
        "status": "algebraically_verified_modulo_L",
    }


def write_candidate_lemmas(candidates: list[LemmaCandidate], test_rows: list[dict[str, object]]) -> None:
    tests_by_id = {int(row["lemma_id"]): row for row in test_rows}
    lines = [
        "# Candidate Remaining Lemmas",
        "",
        "These are candidate lemmas for the remaining symbolic core. They are not",
        "a proof of the Erdos-Straus conjecture.",
        "",
    ]
    for candidate in candidates:
        test = tests_by_id.get(candidate.lemma_id, {})
        passed = test.get("passed", False)
        if test.get("status") == "algebraically_verified_modulo_L":
            status = "proven algebraically for the stated residue condition"
        elif test.get("status", "").startswith("failed"):
            status = "failed"
        elif test.get("status", "").startswith("skipped"):
            status = "conjectural; residue test skipped by size limit"
        else:
            status = candidate.status
        lines.extend(
            [
                f"## Lemma candidate {candidate.lemma_id}: {candidate.title}",
                "",
                "Claim:",
                f"  {candidate.claim}",
                "",
                "Conditions:",
                f"  condition_type = {candidate.condition_type}",
                f"  condition_modulus = {candidate.condition_modulus}",
                f"  condition_residues = {list(candidate.condition_residues)[:30]}"
                + (" ..." if len(candidate.condition_residues) > 30 else ""),
                "",
                "Rule:",
                f"  d = {candidate.d}",
                f"  a = {candidate.a}",
                f"  b = {candidate.b}",
                "",
                "Why it might work:",
                f"  {candidate.why}",
                "",
                "Residue test:",
                f"  status = {test.get('status', 'not_tested')}",
                f"  L = {test.get('L', '')}",
                f"  tested_residues = {test.get('tested_residues', '')}",
                f"  failed_residue = {test.get('failed_residue', '')}",
                "",
                "Status:",
                f"  {status}",
                "",
            ]
        )
        if not passed and test.get("failed_residue", "") != "":
            lines.append("  This candidate should not be used as a lemma without revision.")
            lines.append("")
    lines.append("No statement here is a proof of the full conjecture.")
    Path("candidate_remaining_lemmas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_promising_focus(remaining: list[RemainderRow]) -> int:
    summary_ratios: list[tuple[float, int]] = []
    for focus_r in FOCUS_RESIDUES:
        summary_path = Path(f"symbolic_remainder_focus_{focus_r}_summary.csv")
        if summary_path.exists():
            row = read_csv_rows(summary_path)[0]
            ratio = int(row["remaining_remainders"]) / max(int(row["initial_remainders"]), 1)
            summary_ratios.append((ratio, focus_r))
    if summary_ratios:
        return min(summary_ratios)[1]
    counts = Counter(row.focus_r for row in remaining)
    return counts.most_common()[-1][0] if counts else FOCUS_RESIDUES[0]


def write_focus_report(
    focus_r: int,
    remaining: list[RemainderRow],
    sample_rules: list[dict[str, object]],
    candidates: list[LemmaCandidate],
    tests: list[dict[str, object]],
) -> None:
    focus_rows = [row for row in remaining if row.focus_r == focus_r]
    focus_sample = [row for row in sample_rules if row["focus_r"] == focus_r]
    q_factor_counter: Counter[int] = Counter()
    q_counter: Counter[int] = Counter()
    for row in focus_rows:
        q_counter.update(row.visible_q_values)
        for q in row.visible_q_values:
            q_factor_counter.update(prime_factors(q))
    d_counter = Counter(int(row["d"]) for row in focus_sample if row["d"] != "")
    pair_counter = Counter((int(row["a"]), int(row["b"])) for row in focus_sample if row["a"] != "")
    passed_tests = [row for row in tests if row["passed"]]
    failed_tests = [row for row in tests if not row["passed"]]
    best_candidate = candidates[0] if candidates else None
    lines = [
        f"# Focus {focus_r} Human Lemma Report",
        "",
        "This is a local diagnostic report, not a proof of the full conjecture.",
        "",
        "## What Remains",
        "",
        f"Remaining symbolic remainders for this focus: `{len(focus_rows)}`.",
        f"Top visible q values: `{top_counter_text(q_counter)}`.",
        f"Top visible q prime factors: `{top_counter_text(q_factor_counter)}`.",
        "",
        "## Dominant Sample Rules",
        "",
        f"Top d: `{top_counter_text(d_counter)}`.",
        f"Top pairs: `{top_counter_text(pair_counter)}`.",
        "",
        "## Best Candidate",
        "",
    ]
    if best_candidate:
        test = next((row for row in tests if int(row["lemma_id"]) == best_candidate.lemma_id), {})
        lines.extend(
            [
                f"Candidate: `{best_candidate.title}`.",
                f"Claim: {best_candidate.claim}",
                f"Residue-test status: `{test.get('status', 'not_tested')}`.",
            ]
        )
    else:
        lines.append("No candidate lemma generated.")
    lines.extend(
        [
            "",
            "## What Would Be Needed",
            "",
            "A useful next lemma should simplify the visible negative q-conditions",
            "without taking the full lcm of all conditions. The current promising",
            "direction is to prove dominance or impossibility relations among",
            "small q residue sets.",
            "",
            f"Passed residue tests: `{len(passed_tests)}`.",
            f"Failed or skipped residue tests: `{len(failed_tests)}`.",
            "",
            "Verdict: not proved yet.",
        ]
    )
    Path(f"focus_{focus_r}_human_lemma_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def print_final_report(
    remaining: list[RemainderRow],
    sample_rules: list[dict[str, object]],
    comparison: list[dict[str, object]],
    tests: list[dict[str, object]],
    sampled: bool,
) -> None:
    q_factor_counter: Counter[int] = Counter()
    q_counter: Counter[int] = Counter()
    for row in remaining:
        q_counter.update(row.visible_q_values)
        for q in row.visible_q_values:
            q_factor_counter.update(prime_factors(q))
    d_counter = Counter(int(row["d"]) for row in sample_rules if row["d"] != "")
    pair_counter = Counter((int(row["a"]), int(row["b"])) for row in sample_rules if row["a"] != "")
    passed = [row for row in tests if row["passed"]]
    failed = [row for row in tests if not row["passed"]]

    print(f"Total remaining remainders analyzed: {len(remaining)}")
    if sampled:
        print("sampled analysis only")
    print(f"Top common features: {[row['feature'] for row in comparison[:5]]}")
    print(f"Top missing primes / q factors: {q_factor_counter.most_common(10)}")
    print(f"Top minimal d: {d_counter.most_common(10)}")
    print(f"Top pairs (a,b): {pair_counter.most_common(10)}")
    print("Best simple patterns: see remaining_simple_patterns.md")
    print("Candidate lemmas: see candidate_remaining_lemmas.md")
    print(f"Lemma candidates passed residue tests: {[row['lemma_id'] for row in passed]}")
    print(
        "Lemma candidates failed/skipped: "
        f"{[(row['lemma_id'], row['status'], row['failed_residue']) for row in failed]}"
    )
    print(
        "Best next mathematical direction: prove dominance/impossibility among "
        "negative q-residue conditions without expanding to their full lcm."
    )
    print("Verdict: not proved yet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find simple lemma candidates in remaining symbolic core.")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=0,
        help="Limit remaining remainders analyzed, spread across focus residues. 0 means all.",
    )
    parser.add_argument(
        "--sample-per-focus",
        type=int,
        default=500,
        help="Remainder samples per focus for minimal-rule analysis.",
    )
    parser.add_argument(
        "--max-d",
        type=int,
        default=100_000,
        help="Fallback max d for minimal general-key search when diagnostics lack a row.",
    )
    parser.add_argument(
        "--max-rule-q",
        type=int,
        default=1_000_000,
        help="Maximum q to enumerate when building candidate rule residue sets.",
    )
    parser.add_argument(
        "--max-test-L",
        type=int,
        default=2_000_000,
        help="Maximum modulus L for candidate lemma residue tests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    remaining, missing_required = load_remainders(args.sample_limit)
    optional_missing = [path for path in OPTIONAL_PATHS if not path.exists()]
    for focus_r in FOCUS_RESIDUES:
        for path in (
            Path(f"symbolic_remainder_focus_{focus_r}_selected_rules.csv"),
            Path(f"symbolic_cover_focus_{focus_r}_selected_rules.csv"),
        ):
            if not path.exists():
                optional_missing.append(path)

    if missing_required:
        print("Missing required remaining files:")
        for path in missing_required:
            print(f"  - {path}")
        raise SystemExit(1)
    if optional_missing:
        print("Missing optional context files:")
        for path in optional_missing:
            print(f"  - {path}")

    sampled = bool(args.sample_limit)
    feature_rows = features_csv_rows(remaining)
    write_csv(Path("remaining_core_features.csv"), list(feature_rows[0].keys()) if feature_rows else [], feature_rows)

    diagnostics_rows = load_diagnostics_rows()
    comparison = comparison_rows(remaining, diagnostics_rows)
    write_csv(
        Path("remaining_vs_covered_comparison.csv"),
        ["feature", "remaining_count", "covered_count", "enrichment_ratio"],
        comparison,
    )

    sample_rules = sample_minimal_rule_rows(remaining, args.max_d, args.sample_per_focus)
    write_csv(
        Path("remaining_sample_minimal_rules.csv"),
        [
            "focus_r",
            "base_modulus",
            "base_residue",
            "sample_n",
            "d",
            "a",
            "b",
            "x",
            "y",
            "z",
            "verified",
            "rule_modulus",
            "rule_prime_factors",
            "sample_satisfies_visible_conditions",
            "source",
            "why_not_closed_earlier",
        ],
        sample_rules,
    )

    write_simple_patterns(remaining, comparison, sample_rules)
    rule_sets = load_rule_residue_sets()
    candidates = generate_lemma_candidates(sample_rules, rule_sets, args.max_rule_q)
    tests = [test_candidate(candidate, args.max_test_L) for candidate in candidates]
    write_csv(
        Path("candidate_lemma_tests.csv"),
        ["lemma_id", "d", "a", "b", "L", "tested_residues", "passed", "failed_residue", "status"],
        tests,
    )
    write_candidate_lemmas(candidates, tests)

    focus_r = choose_promising_focus(remaining)
    write_focus_report(focus_r, remaining, sample_rules, candidates, tests)
    print_final_report(remaining, sample_rules, comparison, tests, sampled)


if __name__ == "__main__":
    main()
