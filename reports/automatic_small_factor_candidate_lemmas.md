# Candidate Family Lemmas by Prime Factors

These are candidate local lemmas for the hard core `n == 1 mod 24`.
Each lemma still needs independent mathematical review. They are not a
proof of the full Erdos-Straus conjecture.

## Lemma candidate 1: G: one dominant prime factor

Claim: For a fixed dominant-prime rule, if every non-p prime-power factor of lcm(a,b) is automatic on n == 1 mod 24, then only the condition n == 0 or -d mod p remains.

Why it might work: This is exact for each listed rule, but not yet a single closed-form family.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Lemma candidate 2: F2: a=2, b=2p, p=2d-1

Claim: If d == 3 mod 4 and p=2d-1 is prime, then for n == 1 mod 24 the rule (d,2,2p) works whenever n == 0 or -d mod p.

Why it might work: The factor 2 is automatic because n and d are odd.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Lemma candidate 3: F1: a=1, b=p=4d-1

Claim: If d == 3 mod 4 and p=4d-1 is prime, then for n == 1 mod 24 the rule (d,1,p) works whenever n == 0 or -d mod p.

Why it might work: No small a/b factors remain after p.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Lemma candidate 4: F3: a=3, b=p=4d-3

Claim: If d == 11 mod 12 and p=4d-3 is prime, then for n == 1 mod 24 the rule (d,3,p) works whenever n == 0 or -d mod p.

Why it might work: The factor 3 is automatic because n == 1 mod 3 and d == 2 mod 3.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Lemma candidate 5: F4: a=6, b=2p, p=2d-3

Claim: If d == 11 mod 12 and p=2d-3 is prime, then for n == 1 mod 24 the rule (d,6,2p) works whenever n == 0 or -d mod p.

Why it might work: The factors 2 and 3 are automatic.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Lemma candidate 6: F5: a=24, b=4p, p=d-6

Claim: If d == 23 mod 24 and p=d-6 is prime, then for n == 1 mod 24 the rule (d,24,4p) works whenever n == 0 or -d mod p.

Why it might work: The factors 8 and 3 are automatic because n+d == 0 mod 24.

Conclusion:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

Status: algebraically verified for the listed fixed rules by finite
residue tests; conjectural as a reusable family until reviewed by hand.

## Guardrail

No full proof is claimed here. These lemmas only describe local
rule families that may help compress the remaining core.
