# Prime-Factor Family Lemma Candidates

This file looks for reusable rule families in `(d,a,b)` using prime
factors of `q = lcm(4,a,b)`. It is not a proof of the full
Erdos-Straus conjecture.

## General Prime-Power Lemma

For any fixed `d,a,b` with `a+b=4d`, let `L = lcm(a,b)`. If
`n+d` is divisible by `4` and for every prime power `ell = p^e`
dividing `L` we have `n(n+d) == 0 mod ell`, then

`x=(n+d)/4`, `y=n(n+d)/a`, `z=n(n+d)/b`

is a valid general-key solution. This is algebraic: the prime-power
conditions imply `a | n(n+d)` and `b | n(n+d)`.

## Frequent Families

- `G: one dominant prime factor in lcm(a,b)`: 212 analyzed rules
- `F2: a=2, b=2p, p=2d-1`: 13 analyzed rules
- `F1: a=1, b=p=4d-1`: 9 analyzed rules
- `F4: a=6, b=2p, p=2d-3`: 6 analyzed rules
- `F3: a=3, b=p=4d-3`: 5 analyzed rules
- `F5: a=24, b=4p, p=d-6`: 5 analyzed rules

## Concrete Candidate Families

### d=11, pair=(1,43), q=172

- template: `F1: a=1, b=p=4d-1`
- support_count: `25844`
- lcm(a,b): `43 = 43`
- rule residues modulo q: `129;161`
- local prime-power conditions: `43^1 mod 43: [0, 32]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;32`
- hard-core condition equals {0,-d} mod p: `True`

### d=11, pair=(3,41), q=492

- template: `F3: a=3, b=p=4d-3`
- support_count: `25707`
- lcm(a,b): `123 = 3*41`
- rule residues modulo q: `153;205;369;481`
- local prime-power conditions: `3^1 mod 3: [0, 1]; 41^1 mod 41: [0, 30]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;30`
- hard-core condition equals {0,-d} mod p: `True`

### d=19, pair=(2,74), q=148

- template: `F2: a=2, b=2p, p=2d-1`
- support_count: `23091`
- lcm(a,b): `74 = 2*37`
- rule residues modulo q: `37;129`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 37^1 mod 37: [0, 18]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;18`
- hard-core condition equals {0,-d} mod p: `True`

### d=15, pair=(1,59), q=236

- template: `F1: a=1, b=p=4d-1`
- support_count: `17612`
- lcm(a,b): `59 = 59`
- rule residues modulo q: `177;221`
- local prime-power conditions: `59^1 mod 59: [0, 44]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;44`
- hard-core condition equals {0,-d} mod p: `True`

### d=11, pair=(6,38), q=228

- template: `F4: a=6, b=2p, p=2d-3`
- support_count: `13161`
- lcm(a,b): `114 = 2*3*19`
- rule residues modulo q: `57;133;141;217`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 3^1 mod 3: [0, 1]; 19^1 mod 19: [0, 8]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;8`
- hard-core condition equals {0,-d} mod p: `True`

### d=27, pair=(2,106), q=212

- template: `F2: a=2, b=2p, p=2d-1`
- support_count: `12325`
- lcm(a,b): `106 = 2*53`
- rule residues modulo q: `53;185`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 53^1 mod 53: [0, 26]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;26`
- hard-core condition equals {0,-d} mod p: `True`

### d=15, pair=(2,58), q=116

- template: `F2: a=2, b=2p, p=2d-1`
- support_count: `11940`
- lcm(a,b): `58 = 2*29`
- rule residues modulo q: `29;101`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 29^1 mod 29: [0, 14]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;14`
- hard-core condition equals {0,-d} mod p: `True`

### d=23, pair=(24,68), q=408

- template: `F5: a=24, b=4p, p=d-6`
- support_count: `11904`
- lcm(a,b): `408 = 2^3*3*17`
- rule residues modulo q: `153;249;289;385`
- local prime-power conditions: `2^3 mod 8: [0, 1]; 3^1 mod 3: [0, 1]; 17^1 mod 17: [0, 11]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;11`
- hard-core condition equals {0,-d} mod p: `True`

### d=31, pair=(2,122), q=244

- template: `F2: a=2, b=2p, p=2d-1`
- support_count: `11658`
- lcm(a,b): `122 = 2*61`
- rule residues modulo q: `61;213`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 61^1 mod 61: [0, 30]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;30`
- hard-core condition equals {0,-d} mod p: `True`

### d=11, pair=(15,29), q=1740

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `11603`
- lcm(a,b): `435 = 3*5*29`
- rule residues modulo q: `105;145;609;685;1149;1189;1305;1729`
- local prime-power conditions: `3^1 mod 3: [0, 1]; 5^1 mod 5: [0, 4]; 29^1 mod 29: [0, 18]`
- hard-core n == 1 mod 24 residues modulo dominant p: ``
- hard-core condition equals {0,-d} mod p: `False`

### d=23, pair=(3,89), q=1068

- template: `F3: a=3, b=p=4d-3`
- support_count: `10343`
- lcm(a,b): `267 = 3*89`
- rule residues modulo q: `333;445;801;1045`
- local prime-power conditions: `3^1 mod 3: [0, 1]; 89^1 mod 89: [0, 66]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;66`
- hard-core condition equals {0,-d} mod p: `True`

### d=19, pair=(14,62), q=868

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `10254`
- lcm(a,b): `434 = 2*7*31`
- rule residues modulo q: `93;105;217;849`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 7^1 mod 7: [0, 2]; 31^1 mod 31: [0, 12]`
- hard-core n == 1 mod 24 residues modulo dominant p: ``
- hard-core condition equals {0,-d} mod p: `False`

### d=23, pair=(23,69), q=276

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `10043`
- lcm(a,b): `69 = 3*23`
- rule residues modulo q: `69;253`
- local prime-power conditions: `3^1 mod 3: [0, 1]; 23^1 mod 23: [0]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0`
- hard-core condition equals {0,-d} mod p: `False`

### d=23, pair=(6,86), q=516

- template: `F4: a=6, b=2p, p=2d-3`
- support_count: `10015`
- lcm(a,b): `258 = 2*3*43`
- rule residues modulo q: `129;301;321;493`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 3^1 mod 3: [0, 1]; 43^1 mod 43: [0, 20]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;20`
- hard-core condition equals {0,-d} mod p: `True`

### d=35, pair=(6,134), q=804

- template: `F4: a=6, b=2p, p=2d-3`
- support_count: `9316`
- lcm(a,b): `402 = 2*3*67`
- rule residues modulo q: `201;469;501;769`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 3^1 mod 3: [0, 1]; 67^1 mod 67: [0, 32]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;32`
- hard-core condition equals {0,-d} mod p: `True`

### d=7, pair=(11,17), q=748

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `8920`
- lcm(a,b): `187 = 11*17`
- rule residues modulo q: `561;605;697;741`
- local prime-power conditions: `11^1 mod 11: [0, 4]; 17^1 mod 17: [0, 10]`
- hard-core n == 1 mod 24 residues modulo dominant p: ``
- hard-core condition equals {0,-d} mod p: `False`

### d=35, pair=(2,138), q=276

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `8543`
- lcm(a,b): `138 = 2*3*23`
- rule residues modulo q: `57;69;241;253`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 3^1 mod 3: [0, 1]; 23^1 mod 23: [0, 11]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;11`
- hard-core condition equals {0,-d} mod p: `True`

### d=19, pair=(5,71), q=1420

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `7855`
- lcm(a,b): `355 = 5*71`
- rule residues modulo q: `265;781;1065;1401`
- local prime-power conditions: `5^1 mod 5: [0, 1]; 71^1 mod 71: [0, 52]`
- hard-core n == 1 mod 24 residues modulo dominant p: ``
- hard-core condition equals {0,-d} mod p: `False`

### d=47, pair=(2,186), q=372

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `7477`
- lcm(a,b): `186 = 2*3*31`
- rule residues modulo q: `93;201;217;325`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 3^1 mod 3: [0, 1]; 31^1 mod 31: [0, 15]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;15`
- hard-core condition equals {0,-d} mod p: `True`

### d=27, pair=(1,107), q=428

- template: `F1: a=1, b=p=4d-1`
- support_count: `7396`
- lcm(a,b): `107 = 107`
- rule residues modulo q: `321;401`
- local prime-power conditions: `107^1 mod 107: [0, 80]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;80`
- hard-core condition equals {0,-d} mod p: `True`

### d=39, pair=(8,148), q=296

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `7323`
- lcm(a,b): `296 = 2^3*37`
- rule residues modulo q: `185;257`
- local prime-power conditions: `2^3 mod 8: [0, 1]; 37^1 mod 37: [0, 35]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;35`
- hard-core condition equals {0,-d} mod p: `True`

### d=31, pair=(8,116), q=232

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `6511`
- lcm(a,b): `232 = 2^3*29`
- rule residues modulo q: `145;201`
- local prime-power conditions: `2^3 mod 8: [0, 1]; 29^1 mod 29: [0, 27]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;27`
- hard-core condition equals {0,-d} mod p: `True`

### d=47, pair=(4,184), q=184

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `6371`
- lcm(a,b): `184 = 2^3*23`
- rule residues modulo q: `137;161`
- local prime-power conditions: `2^3 mod 8: [0, 1]; 23^1 mod 23: [0, 22]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;22`
- hard-core condition equals {0,-d} mod p: `True`

### d=47, pair=(24,164), q=984

- template: `F5: a=24, b=4p, p=d-6`
- support_count: `5429`
- lcm(a,b): `984 = 2^3*3*41`
- rule residues modulo q: `369;609;697;937`
- local prime-power conditions: `2^3 mod 8: [0, 1]; 3^1 mod 3: [0, 1]; 41^1 mod 41: [0, 35]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0;35`
- hard-core condition equals {0,-d} mod p: `True`

### d=31, pair=(62,62), q=124

- template: `G: one dominant prime factor in lcm(a,b)`
- support_count: `5336`
- lcm(a,b): `62 = 2*31`
- rule residues modulo q: `93`
- local prime-power conditions: `2^1 mod 2: [0, 1]; 31^1 mod 31: [0]`
- hard-core n == 1 mod 24 residues modulo dominant p: `0`
- hard-core condition equals {0,-d} mod p: `False`

## Test Summary

Prime-power factorization tests passed: `250`.
Prime-power factorization tests failed: `0`.
Hard-core dominant-prime reductions found: `69`.

Important: these are local family lemmas and diagnostics. They do
not prove that the remaining core is fully covered.

Verdict: not proved yet.
