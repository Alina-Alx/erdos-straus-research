# Remaining Simple Patterns

These are human-readable diagnostics, not proof claims.

Total remaining remainders analyzed: `286082`.
Condition summaries truncated: `286082` (100.00% of analyzed rows).
Top reported condition counts: `58:34910, 59:27792, 56:22810, 55:22345, 57:20988, 61:20718, 60:19691, 54:18436, 64:15021, 53:14599`.
Top gcd(r,m): `1:286082`.
r mod 24 distribution: `1:286082`.
Top visible excluded q values: `404:286082, 556:286082, 2796:286082, 488:280867, 568:280192, 436:278706, 1128:254582, 248:236170, 428:228475, 244:227048`.
Top visible q prime factors: `2:11443280, 3:3928020, 5:2618194, 7:1124515, 71:1090203, 47:717237, 61:680186, 53:581564, 31:547749, 79:497750`.

## Quadratic-Residue Rates

- mod 5: 286082/286082 = 100.00%
- mod 7: 286082/286082 = 100.00%
- mod 11: 286082/286082 = 100.00%
- mod 13: 286082/286082 = 100.00%
- mod 17: 181165/286082 = 63.33%
- mod 19: 177079/286082 = 61.90%
- mod 29: 169038/286082 = 59.09%
- mod 23: 159331/286082 = 55.69%
- mod 31: 152722/286082 = 53.38%
- mod 37: 148588/286082 = 51.94%
- mod 41: 148442/286082 = 51.89%
- mod 47: 147352/286082 = 51.51%
- mod 43: 147331/286082 = 51.50%
- mod 53: 146363/286082 = 51.16%
- mod 59: 146086/286082 = 51.06%

## Sample Minimal Rules

Top minimal d: `11:302, 23:241, 19:181, 35:168, 47:148, 31:145, 15:133, 39:122, 27:106, 71:95`.
Top minimal pairs: `(1, 43):108, (2, 74):93, (3, 41):89, (1, 59):72, (2, 122):64, (2, 106):51, (6, 86):49, (24, 68):48, (15, 29):47, (6, 38):47`.
Top sample rule-modulus prime factors: `2:2500, 3:1039, 5:357, 43:239, 7:211, 23:204, 37:195, 29:195, 31:195, 17:177`.

## Enriched Simple Features

- `is_integer_square=True`: remaining=218, covered=2, enrichment=8.595958501408687
- `focus=289`: remaining=59011, covered=2623, enrichment=1.7741996772608857
- `r_mod_11=3`: remaining=59011, covered=2623, enrichment=1.7741996772608857
- `r_mod_13=3`: remaining=59011, covered=2623, enrichment=1.7741996772608857
- `r_mod_840=289`: remaining=59011, covered=2623, enrichment=1.7741996772608857
- `r_mod_7=2`: remaining=116864, covered=5486, enrichment=1.679936074659809
- `r_mod_19=4`: remaining=18213, covered=870, enrichment=1.6509352756106337
- `r_mod_17=13`: remaining=19795, covered=976, enrichment=1.599460431412477
- `focus=961`: remaining=57853, covered=2863, enrichment=1.5935744156927736
- `r_mod_11=4`: remaining=57853, covered=2863, enrichment=1.5935744156927736
- `r_mod_13=12`: remaining=57853, covered=2863, enrichment=1.5935744156927736
- `r_mod_840=121`: remaining=57853, covered=2863, enrichment=1.5935744156927736
- `r_mod_17=8`: remaining=23457, covered=1176, enrichment=1.5730153417551611
- `r_mod_17=12`: remaining=19545, covered=994, enrichment=1.5506618510146455
- `r_mod_17=1`: remaining=22171, covered=1145, enrichment=1.5270301344876567
- `r_mod_17=9`: remaining=21427, covered=1115, enrichment=1.5154943251712176
- `r_mod_17=14`: remaining=14602, covered=773, enrichment=1.4897063275166411
- `r_mod_29=23`: remaining=11963, covered=648, enrichment=1.4559045694919035
- `r_mod_17=2`: remaining=25144, covered=1414, enrichment=1.4023382204132984
- `r_mod_23=12`: remaining=14514, covered=829, enrichment=1.3807034195000685

## Short Read

The remaining core is still dominated by residue-class structure and
large stacks of visible q-exclusions. A clean one-prime separator did
not emerge from this pass; candidate lemmas below test both fixed-rule
residue sets and deliberately simpler conditions.
