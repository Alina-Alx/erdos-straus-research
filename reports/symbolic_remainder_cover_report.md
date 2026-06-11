# Symbolic Remainder Cover Report

This report is a research diagnostic. It does not claim a proof of the
Erdos-Straus conjecture and it does not create a proof certificate.

## Method

Symbolic remainders keep the unresolved space as a base congruence plus
negative residue-set conditions. Applying a new fixed rule either removes
a fully covered remainder, adds another negative condition to a partial
remainder, or records unknown fullness when exact refinement would be too
large. No huge lifted subresidue tree is materialized.

Partial coverage and unknown fullness are not proof coverage.
The `unknown` column counts unique remainders that received at least
one symbolic reduction whose exact full/partial status exceeded the
configured refinement-ratio limit; it can overlap with later full
removals and should be read as a diagnostic warning, not progress
toward a proof.

## Focus Results

| focus | initial | empty removed | full | partial reduced | remaining | unknown | rules | validation failures | verdict |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 289 | 60963 | 0 | 1952 | 0 | 59011 | 60615 | 50 | 0 | not proved yet |
| 361 | 60447 | 0 | 4064 | 0 | 56383 | 59270 | 50 | 0 | not proved yet |
| 529 | 65129 | 0 | 3967 | 0 | 61162 | 64327 | 50 | 0 | not proved yet |
| 841 | 58808 | 0 | 7135 | 0 | 51673 | 56444 | 50 | 0 | not proved yet |
| 961 | 59722 | 0 | 1869 | 0 | 57853 | 59457 | 50 | 0 | not proved yet |

## Main Rules

Top selected `d`: `143:32, 215:23, 239:17, 167:14, 191:12, 159:12, 111:10, 199:9, 131:7, 135:6`.

Top selected pairs `(a,b)`: `(8, 564):5, (12, 752):5, (4, 568):5, (12, 656):5, (4, 664):4, (12, 848):4, (8, 852):4, (4, 536):4, (12, 944):4, (2, 426):3`.

## Interpretation

A large number of remaining classes receiving additional negative
conditions is evidence that symbolic compression is useful. It is not
a proof unless the remaining count reaches zero with no validation
failures and no unknown-fullness coverage.

Candidate local focus covers: none.

Verdict: not proved yet.
