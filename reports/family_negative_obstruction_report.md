# Family Negative-Condition Obstruction Report

This report explains why direct implications such as
`Base AND NOT(A) => B` did not appear in the sampled search.

## Summary

- attempts analyzed: `32000`
- status counts: `[('unknown_large_ratio', 24000), ('failed', 8000)]`
- top fresh target moduli: `[('61', 6400), ('53', 5400), ('59', 4000), ('17', 4000), ('29', 3800), ('37', 3000), ('19', 2000), ('89', 1200), ('41', 1000), ('5;29', 1000), ('5', 200)]`
- top fresh target primes: `[(61, 6400), (53, 5400), (29, 4800), (59, 4000), (17, 4000), (37, 3000), (19, 2000), (5, 1200), (89, 1200), (41, 1000)]`

## Obstruction Lemma Candidate

Claim shape:

```text
If the target family condition contains a modulus q_target that is
coprime to all moduli appearing in the base/negative assumptions,
then the negative assumptions usually cannot force the target.
CRT supplies residues satisfying the negatives while avoiding target.
```

Status: computationally supported by the failed/unknown implication
attempts. This is an obstruction lemma, not a cover lemma.

## Consequence

A successful next lemma probably cannot be only:

```text
NOT(rule_1) AND NOT(rule_2) => rule_3
```

It must either:

- group rules by shared prime moduli, so the target prime is not fresh;
- use a covering statement over a fixed small prime set;
- or prove a structural reason that the base class already restricts
  the target prime.

Verdict: not proved yet.
