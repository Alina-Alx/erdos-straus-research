# Candidate Lemmas

These notes do not prove the Erdos-Straus conjecture.
They separate algebraic facts from computationally supported patterns.

## Lemma Candidate A

Status: computationally supported.

For hard classes `n == p^2 mod 120120`, unresolved leaves often
require lifts by primes `q` appearing in the fixed-rule pair `(a,b)`.
A symbolic split by `q` may cover large repeated families.

## Lemma Candidate B

Status: proven algebraically.

For a fixed general-key rule `(d,a,b)`, applicability depends only on
`n mod q` for `q = lcm(4,a,b)`: the checks `(n+d) mod 4`,
`n(n+d) mod a`, and `n(n+d) mod b` are congruence checks modulo
divisors of `q`. Therefore the rule has a finite residue set modulo `q`.

## Lemma Candidate C

Status: conjectural as a cover strategy; algebraically valid as a
representation of one rule split.

If a class `C = (m,r)` is not covered by a sample rule `(d,a,b)` and
the needed lift introduces a missing factor `q`, keep the symbolic
condition `n mod lcm(4,a,b) in S_rule` and use CRT intersections
instead of explicitly materializing all lifted subresidues.

## Guardrail

A symbolic planner can compress repeated congruence families, but a
full cover still needs independently checked coverage of every class
represented by the planner.
