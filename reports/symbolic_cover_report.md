# Symbolic Cover Report

This report is a research diagnostic. It does not claim a proof of the
Erdos-Straus conjecture and it does not turn partial symbolic coverage
into a proof.

## Method

A fixed general-key rule `(d,a,b)` works on a residue set modulo
`q = lcm(4,a,b)`. A recursive unresolved leaf is kept as one class
`n == r (mod m)`. CRT decides whether that class intersects a rule
residue without enumerating all lifted subclasses.

A class is counted as fully covered only when finite refinement was
checked under the configured ratio limit and sample solutions passed
`check_solution`. Partial intersections become symbolic remainders of
the form `base class AND not S_rule`. Unknown fullness stays a candidate
state, never proof coverage.

## Focus Runs

| focus | classes | full | partial | uncovered | unknown | remainders | rules | validation failures | verdict |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 289 | 61634 | 671 | 60963 | 0 | 0 | 60963 | 30 | 0 | not proved yet |
| 361 | 60983 | 536 | 60447 | 0 | 0 | 60447 | 30 | 0 | not proved yet |
| 529 | 65519 | 390 | 65129 | 0 | 0 | 65129 | 30 | 0 | not proved yet |
| 841 | 59791 | 983 | 58808 | 0 | 0 | 58808 | 30 | 0 | not proved yet |
| 961 | 60716 | 994 | 59722 | 0 | 0 | 59722 | 30 | 0 | not proved yet |

## Master Keys Selected

Top selected `d`: `59:26, 63:14, 55:13, 35:12, 51:10, 87:8, 39:8, 79:8, 31:7, 71:6`.

Top selected pairs `(a,b)`: `(4, 248):5, (1, 139):5, (2, 202):5, (2, 218):5, (8, 244):5, (3, 233):5, (4, 344):4, (8, 212):4, (2, 122):4, (1, 107):4`.

| count | d | a | b | q |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 63 | 4 | 248 | 248 |
| 5 | 35 | 1 | 139 | 556 |
| 5 | 51 | 2 | 202 | 404 |
| 5 | 55 | 2 | 218 | 436 |
| 5 | 63 | 8 | 244 | 488 |
| 5 | 59 | 3 | 233 | 2796 |
| 4 | 87 | 4 | 344 | 344 |
| 4 | 55 | 8 | 212 | 424 |
| 4 | 31 | 2 | 122 | 244 |
| 4 | 27 | 1 | 107 | 428 |
| 4 | 35 | 3 | 137 | 1644 |
| 3 | 23 | 3 | 89 | 1068 |
| 3 | 59 | 6 | 230 | 1380 |
| 3 | 79 | 20 | 296 | 1480 |
| 3 | 59 | 1 | 235 | 940 |

## Coverage Boundary

Fully checked finite coverage appears in the `full` column above.
Symbolic remainders are still open local conditions; they are smaller
descriptions of unresolved work, not closed classes.

Candidate local focus covers: none.

Verdict: not proved yet.
