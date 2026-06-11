# Family Negative-Condition Implication Report

This report searches for local implications of the form:

```text
Base AND NOT(A) => B
Base AND NOT(A) AND NOT(B) => C
```

where `A`, `B`, and `C` are prime-factor family conditions. The checks
are finite residue tests modulo the relevant lcm, capped by a refinement
ratio. This is not a proof of the full Erdős-Straus conjecture.

Sampled analysis only: `yes`.

## Focus Summaries

### focus 289

- remainders sampled: `200`
- forced implications found: `0`
- no-candidate classes: `0`
- status counts: `[('unknown_large_ratio', 5000), ('failed', 1400)]`
- top implication patterns: `[]`

### focus 361

- remainders sampled: `200`
- forced implications found: `0`
- no-candidate classes: `0`
- status counts: `[('unknown_large_ratio', 4800), ('failed', 1600)]`
- top implication patterns: `[]`

### focus 529

- remainders sampled: `200`
- forced implications found: `0`
- no-candidate classes: `0`
- status counts: `[('unknown_large_ratio', 4800), ('failed', 1600)]`
- top implication patterns: `[]`

### focus 841

- remainders sampled: `200`
- forced implications found: `0`
- no-candidate classes: `0`
- status counts: `[('unknown_large_ratio', 4600), ('failed', 1800)]`
- top implication patterns: `[]`

### focus 961

- remainders sampled: `200`
- forced implications found: `0`
- no-candidate classes: `0`
- status counts: `[('unknown_large_ratio', 4800), ('failed', 1600)]`
- top implication patterns: `[]`

## Top Candidate Lemma Patterns

No strong negative-condition forcing pattern was found at this stage.

## Verdict

These are local symbolic implication candidates only. Unknown-large-ratio
cases and failed implications are not hidden; they remain outside any
candidate lemma.

Verdict: not proved yet.
