# Candidate Remaining Lemmas

These are candidate lemmas for the remaining symbolic core. They are not
a proof of the Erdos-Straus conjecture.

## Lemma candidate 1: Fixed residue-set rule d=11, pair=(1,43)

Claim:
  If n mod 172 is in S_rule for d=11, a=1, b=43, then the rule covers n.

Conditions:
  condition_type = mod_in
  condition_modulus = 172
  condition_residues = [129, 161]

Rule:
  d = 11
  a = 1
  b = 43

Why it might work:
  For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.

Residue test:
  status = algebraically_verified_modulo_L
  L = 172
  tested_residues = 2
  failed_residue = 

Status:
  proven algebraically for the stated residue condition

## Lemma candidate 2: Fixed residue-set rule d=19, pair=(2,74)

Claim:
  If n mod 148 is in S_rule for d=19, a=2, b=74, then the rule covers n.

Conditions:
  condition_type = mod_in
  condition_modulus = 148
  condition_residues = [37, 129]

Rule:
  d = 19
  a = 2
  b = 74

Why it might work:
  For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.

Residue test:
  status = algebraically_verified_modulo_L
  L = 148
  tested_residues = 2
  failed_residue = 

Status:
  proven algebraically for the stated residue condition

## Lemma candidate 3: Fixed residue-set rule d=11, pair=(3,41)

Claim:
  If n mod 492 is in S_rule for d=11, a=3, b=41, then the rule covers n.

Conditions:
  condition_type = mod_in
  condition_modulus = 492
  condition_residues = [153, 205, 369, 481]

Rule:
  d = 11
  a = 3
  b = 41

Why it might work:
  For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.

Residue test:
  status = algebraically_verified_modulo_L
  L = 492
  tested_residues = 4
  failed_residue = 

Status:
  proven algebraically for the stated residue condition

## Lemma candidate 4: Fixed residue-set rule d=15, pair=(1,59)

Claim:
  If n mod 236 is in S_rule for d=15, a=1, b=59, then the rule covers n.

Conditions:
  condition_type = mod_in
  condition_modulus = 236
  condition_residues = [177, 221]

Rule:
  d = 15
  a = 1
  b = 59

Why it might work:
  For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.

Residue test:
  status = algebraically_verified_modulo_L
  L = 236
  tested_residues = 2
  failed_residue = 

Status:
  proven algebraically for the stated residue condition

## Lemma candidate 5: Fixed residue-set rule d=31, pair=(2,122)

Claim:
  If n mod 244 is in S_rule for d=31, a=2, b=122, then the rule covers n.

Conditions:
  condition_type = mod_in
  condition_modulus = 244
  condition_residues = [61, 213]

Rule:
  d = 31
  a = 2
  b = 122

Why it might work:
  For every tested residue t in S_rule, t(t+d) is divisible by a and b, and t+d is divisible by 4.

Residue test:
  status = algebraically_verified_modulo_L
  L = 244
  tested_residues = 2
  failed_residue = 

Status:
  proven algebraically for the stated residue condition

## Lemma candidate 6: Simple congruence attempt for d=11, pair=(1,43)

Claim:
  If n == 1 mod 5, then rule d=11, a=1, b=43 covers n.

Conditions:
  condition_type = mod_eq
  condition_modulus = 5
  condition_residues = [1]

Rule:
  d = 11
  a = 1
  b = 43

Why it might work:
  This congruence was frequent among sampled remaining rows using the same minimal rule.

Residue test:
  status = failed_counterexample_residue
  L = 860
  tested_residues = 1
  failed_residue = 1

Status:
  failed

  This candidate should not be used as a lemma without revision.

## Lemma candidate 7: Simple congruence attempt for d=19, pair=(2,74)

Claim:
  If n == 18 mod 37, then rule d=19, a=2, b=74 covers n.

Conditions:
  condition_type = mod_eq
  condition_modulus = 37
  condition_residues = [18]

Rule:
  d = 19
  a = 2
  b = 74

Why it might work:
  This congruence was frequent among sampled remaining rows using the same minimal rule.

Residue test:
  status = failed_counterexample_residue
  L = 148
  tested_residues = 1
  failed_residue = 18

Status:
  failed

  This candidate should not be used as a lemma without revision.

## Lemma candidate 8: Simple congruence attempt for d=11, pair=(3,41)

Claim:
  If n == 1 mod 5, then rule d=11, a=3, b=41 covers n.

Conditions:
  condition_type = mod_eq
  condition_modulus = 5
  condition_residues = [1]

Rule:
  d = 11
  a = 3
  b = 41

Why it might work:
  This congruence was frequent among sampled remaining rows using the same minimal rule.

Residue test:
  status = failed_counterexample_residue
  L = 2460
  tested_residues = 1
  failed_residue = 1

Status:
  failed

  This candidate should not be used as a lemma without revision.

## Lemma candidate 9: Simple congruence attempt for d=15, pair=(1,59)

Claim:
  If n == 1 mod 5, then rule d=15, a=1, b=59 covers n.

Conditions:
  condition_type = mod_eq
  condition_modulus = 5
  condition_residues = [1]

Rule:
  d = 15
  a = 1
  b = 59

Why it might work:
  This congruence was frequent among sampled remaining rows using the same minimal rule.

Residue test:
  status = failed_counterexample_residue
  L = 1180
  tested_residues = 1
  failed_residue = 1

Status:
  failed

  This candidate should not be used as a lemma without revision.

## Lemma candidate 10: Simple congruence attempt for d=31, pair=(2,122)

Claim:
  If n == 1 mod 5, then rule d=31, a=2, b=122 covers n.

Conditions:
  condition_type = mod_eq
  condition_modulus = 5
  condition_residues = [1]

Rule:
  d = 31
  a = 2
  b = 122

Why it might work:
  This congruence was frequent among sampled remaining rows using the same minimal rule.

Residue test:
  status = failed_counterexample_residue
  L = 1220
  tested_residues = 1
  failed_residue = 1

Status:
  failed

  This candidate should not be used as a lemma without revision.

No statement here is a proof of the full conjecture.
