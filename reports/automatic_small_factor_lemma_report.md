# Automatic Small-Factor Lemma Search

This report searches for family lemmas of the form:

`n == 1 mod 24` plus `n == 0 or -d mod p` implies a fixed
general-key rule `(d,a,b)`.

It does not prove the full Erdos-Straus conjecture.

## Summary

- rules analyzed: `250`
- rules reduced to one dominant-prime condition: `69`
- rules not reduced by this test: `181`
- common nonautomatic small factors: `[('5', 42), ('7', 34), ('9', 23), ('16', 17), ('13', 16), ('11', 15), ('32', 10), ('17', 8), ('25', 8), ('27', 6), ('19', 6), ('23', 5), ('29', 4), ('64', 3), ('31', 3)]`

## Family Candidates

### G: one dominant prime factor

- rules seen: `212`
- rules reduced: `31`
- support count: `331317`
- claim: For a fixed dominant-prime rule, if every non-p prime-power factor of lcm(a,b) is automatic on n == 1 mod 24, then only the condition n == 0 or -d mod p remains.
- automatic factor reason: This is exact for each listed rule, but not yet a single closed-form family.
- examples: `d=11, a=15, b=29, p=29 | d=19, a=14, b=62, p=31 | d=23, a=23, b=69, p=23 | d=7, a=11, b=17, p=17 | d=35, a=2, b=138, p=23 | d=19, a=5, b=71, p=71 | d=47, a=2, b=186, p=31 | d=39, a=8, b=148, p=37`

### F2: a=2, b=2p, p=2d-1

- rules seen: `13`
- rules reduced: `13`
- support count: `103387`
- claim: If d == 3 mod 4 and p=2d-1 is prime, then for n == 1 mod 24 the rule (d,2,2p) works whenever n == 0 or -d mod p.
- automatic factor reason: The factor 2 is automatic because n and d are odd.
- examples: `d=19, a=2, b=74, p=37 | d=27, a=2, b=106, p=53 | d=15, a=2, b=58, p=29 | d=31, a=2, b=122, p=61 | d=51, a=2, b=202, p=101 | d=55, a=2, b=218, p=109 | d=75, a=2, b=298, p=149 | d=79, a=2, b=314, p=157`

### F1: a=1, b=p=4d-1

- rules seen: `9`
- rules reduced: `9`
- support count: `85935`
- claim: If d == 3 mod 4 and p=4d-1 is prime, then for n == 1 mod 24 the rule (d,1,p) works whenever n == 0 or -d mod p.
- automatic factor reason: No small a/b factors remain after p.
- examples: `d=11, a=1, b=43, p=43 | d=15, a=1, b=59, p=59 | d=27, a=1, b=107, p=107 | d=35, a=1, b=139, p=139 | d=63, a=1, b=251, p=251 | d=71, a=1, b=283, p=283 | d=83, a=1, b=331, p=331 | d=87, a=1, b=347, p=347`

### F3: a=3, b=p=4d-3

- rules seen: `5`
- rules reduced: `5`
- support count: `62614`
- claim: If d == 11 mod 12 and p=4d-3 is prime, then for n == 1 mod 24 the rule (d,3,p) works whenever n == 0 or -d mod p.
- automatic factor reason: The factor 3 is automatic because n == 1 mod 3 and d == 2 mod 3.
- examples: `d=11, a=3, b=41, p=41 | d=23, a=3, b=89, p=89 | d=35, a=3, b=137, p=137 | d=59, a=3, b=233, p=233 | d=71, a=3, b=281, p=281`

### F4: a=6, b=2p, p=2d-3

- rules seen: `6`
- rules reduced: `6`
- support count: `50276`
- claim: If d == 11 mod 12 and p=2d-3 is prime, then for n == 1 mod 24 the rule (d,6,2p) works whenever n == 0 or -d mod p.
- automatic factor reason: The factors 2 and 3 are automatic.
- examples: `d=11, a=6, b=38, p=19 | d=23, a=6, b=86, p=43 | d=35, a=6, b=134, p=67 | d=83, a=6, b=326, p=163 | d=71, a=6, b=278, p=139 | d=107, a=6, b=422, p=211`

### F5: a=24, b=4p, p=d-6

- rules seen: `5`
- rules reduced: `5`
- support count: `27077`
- claim: If d == 23 mod 24 and p=d-6 is prime, then for n == 1 mod 24 the rule (d,24,4p) works whenever n == 0 or -d mod p.
- automatic factor reason: The factors 8 and 3 are automatic because n+d == 0 mod 24.
- examples: `d=23, a=24, b=68, p=17 | d=47, a=24, b=164, p=41 | d=95, a=24, b=356, p=89 | d=119, a=24, b=452, p=113 | d=143, a=24, b=548, p=137`

## Interpretation

The F1-F5 templates are the cleanest human-readable candidates.
They explain many repeated rules by reducing all divisibility checks
to one prime condition.  The broader G family is mixed: it often has
extra factors such as 5, 7, 11, 13, or 17 that are not forced by
`n == 1 mod 24`, so those rules need either additional hypotheses or
a different family lemma.

Verdict: not proved yet.
