# Prime-Factor Family Report

Rules analyzed: `250`.
Template distribution: `[('G: one dominant prime factor in lcm(a,b)', 212), ('F2: a=2, b=2p, p=2d-1', 13), ('F1: a=1, b=p=4d-1', 9), ('F4: a=6, b=2p, p=2d-3', 6), ('F3: a=3, b=p=4d-3', 5), ('F5: a=24, b=4p, p=d-6', 5)]`.
Top dominant primes: `[(31, 16), (47, 15), (41, 14), (37, 14), (43, 13), (29, 13), (23, 13), (59, 10), (53, 10), (17, 9), (71, 9), (19, 8), (67, 8), (83, 8), (79, 8)]`.
Hard-core reductions matching `{0,-d} mod p`: `63`.
Prime-power factorization failures: `0`.

The useful mathematical pattern is not a single congruence `n == c mod p`,
but a factorized rule condition: `n+d == 0 mod 4` plus local
prime-power divisibility of `n(n+d)`. For many common rules, after
restricting to the hard core `n == 1 mod 24`, the large-prime part
often reduces to `n == 0 or -d mod p`.

This suggests the next lemma should classify when the small factors
of `lcm(a,b)` are automatic on `n == 1 mod 24`, leaving only a large
prime condition.

Verdict: not proved yet.
