# Parametric Family Lemma Tests

Tested all matching prime-parameter instances with `d <= 20000`.

These are conditional local lemmas for `n == 1 mod 24`; they do not
prove the full Erdős-Straus conjecture.

## F1: (a,b)=(1,p), p=4d-1

Claim: `d == 3 mod 4, p=4d-1 prime, n == 1 mod 24, n == 0 or -d mod p`.

Proof idea: No non-p divisibility remains; p divides n(n+d) by the last condition.

Instances tested: `985`.
Passed: `985`.
Failed: `0`.
Examples: `d=3, p=11, d=11, p=43, d=15, p=59, d=27, p=107, d=35, p=139, d=63, p=251, d=71, p=283, d=83, p=331`.

Algebraic shape:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

## F2: (a,b)=(2,2p), p=2d-1

Claim: `d == 3 mod 4, p=2d-1 prime, n == 1 mod 24, n == 0 or -d mod p`.

Proof idea: n and d are odd, so n+d is even; p divides n(n+d) by the last condition.

Instances tested: `1056`.
Passed: `1056`.
Failed: `0`.
Examples: `d=3, p=5, d=7, p=13, d=15, p=29, d=19, p=37, d=27, p=53, d=31, p=61, d=51, p=101, d=55, p=109`.

Algebraic shape:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

## F3: (a,b)=(3,p), p=4d-3

Claim: `d == 11 mod 12, p=4d-3 prime, n == 1 mod 24, n == 0 or -d mod p`.

Proof idea: n == 1 mod 3 and d == 2 mod 3, so n+d is divisible by 3.

Instances tested: `483`.
Passed: `483`.
Failed: `0`.
Examples: `d=11, p=41, d=23, p=89, d=35, p=137, d=59, p=233, d=71, p=281, d=131, p=521, d=143, p=569, d=155, p=617`.

Algebraic shape:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

## F4: (a,b)=(6,2p), p=2d-3

Claim: `d == 11 mod 12, p=2d-3 prime, n == 1 mod 24, n == 0 or -d mod p`.

Proof idea: The factors 2 and 3 divide n+d; p divides n(n+d) by the last condition.

Instances tested: `530`.
Passed: `530`.
Failed: `0`.
Examples: `d=11, p=19, d=23, p=43, d=35, p=67, d=71, p=139, d=83, p=163, d=107, p=211, d=143, p=283, d=155, p=307`.

Algebraic shape:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

## F5: (a,b)=(24,4p), p=d-6

Claim: `d == 23 mod 24, p=d-6 prime, n == 1 mod 24, n == 0 or -d mod p`.

Proof idea: n+d is divisible by 24; therefore the 24 and 4 factors are automatic.

Instances tested: `289`.
Passed: `289`.
Failed: `0`.
Examples: `d=23, p=17, d=47, p=41, d=95, p=89, d=119, p=113, d=143, p=137, d=239, p=233, d=263, p=257, d=287, p=281`.

Algebraic shape:

```text
x = (n+d)/4
y = n(n+d)/a
z = n(n+d)/b
```

## Verdict

These tests support the family lemmas above, and the proof notes are
simple enough to check by hand.  They are still local compression
lemmas for the hard core, not a full proof certificate.

Verdict: not proved yet.
