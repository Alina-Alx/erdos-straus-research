# Compound Factor Family Lemmas

This report handles G-family rules that do not reduce to one dominant
prime condition on `n == 1 mod 24`.

The candidate lemma shape is:

```text
n == 1 mod 24
n mod p in {0, -d}
n mod h_i in S_i for each extra small factor h_i
```

where `S_i = {t mod h_i : t(t+d) == 0 mod h_i}`.

This is still local rule compression, not a proof of the full conjecture.

## Summary

- G rules needing extra conditions: `181`
- compound local tests passed: `181`
- compound local tests failed: `0`
- top extra moduli: `[('5', 42), ('7', 34), ('9', 23), ('16', 17), ('13', 16), ('11', 15), ('32', 10), ('17', 8), ('25', 8), ('27', 6), ('19', 6), ('23', 5), ('29', 4), ('64', 3), ('31', 3)]`

## Top Compound Families

### extra moduli `5`

- rules seen: `26`
- rules passed: `26`
- support count: `65727`
- examples: `d=11, pair=(15,29), p=29, n mod 5 in {0,4} | d=19, pair=(5,71), p=71, n mod 5 in {0,1} | d=39, pair=(20,136), p=17, n mod 5 in {0,1} | d=39, pair=(1,155), p=31, n mod 5 in {0,1} | d=59, pair=(6,230), p=23, n mod 5 in {0,1} | d=39, pair=(10,146), p=73, n mod 5 in {0,1}`

### extra moduli `7`

- rules seen: `21`
- rules passed: `21`
- support count: `28433`
- examples: `d=19, pair=(14,62), p=31, n mod 7 in {0,2} | d=27, pair=(14,94), p=47, n mod 7 in {0,1} | d=59, pair=(14,222), p=37, n mod 7 in {0,4} | d=47, pair=(42,146), p=73, n mod 7 in {0,2} | d=31, pair=(56,68), p=17, n mod 7 in {0,4} | d=47, pair=(14,174), p=29, n mod 7 in {0,2}`

### extra moduli `9`

- rules seen: `15`
- rules passed: `15`
- support count: `23023`
- examples: `d=23, pair=(18,74), p=37, n mod 9 in {0,4} | d=23, pair=(9,83), p=83, n mod 9 in {0,4} | d=35, pair=(18,122), p=61, n mod 9 in {0,1} | d=35, pair=(9,131), p=131, n mod 9 in {0,1} | d=47, pair=(36,152), p=19, n mod 9 in {0,7} | d=47, pair=(72,116), p=29, n mod 9 in {0,7}`

### extra moduli `11`

- rules seen: `9`
- rules passed: `9`
- support count: `17029`
- examples: `d=7, pair=(11,17), p=17, n mod 11 in {0,4} | d=35, pair=(11,129), p=43, n mod 11 in {0,9} | d=35, pair=(66,74), p=37, n mod 11 in {0,9} | d=35, pair=(22,118), p=59, n mod 11 in {0,9} | d=63, pair=(88,164), p=41, n mod 11 in {0,3} | d=95, pair=(6,374), p=17, n mod 11 in {0,4}`

### extra moduli `16`

- rules seen: `13`
- rules passed: `13`
- support count: `13990`
- examples: `d=47, pair=(16,172), p=43, n mod 16 in {0,1} | d=23, pair=(16,76), p=19, n mod 16 in {0,9} | d=95, pair=(12,368), p=23, n mod 16 in {0,1} | d=63, pair=(16,236), p=59, n mod 16 in {0,1} | d=71, pair=(16,268), p=67, n mod 16 in {0,9} | d=71, pair=(48,236), p=59, n mod 16 in {0,9}`

### extra moduli `13`

- rules seen: `13`
- rules passed: `13`
- support count: `10351`
- examples: `d=23, pair=(39,53), p=53, n mod 13 in {0,3} | d=23, pair=(13,79), p=79, n mod 13 in {0,3} | d=27, pair=(26,82), p=41, n mod 13 in {0,12} | d=43, pair=(26,146), p=73, n mod 13 in {0,9} | d=55, pair=(104,116), p=29, n mod 13 in {0,10} | d=95, pair=(52,328), p=41, n mod 13 in {0,9}`

### extra moduli `27`

- rules seen: `6`
- rules passed: `6`
- support count: `7847`
- examples: `d=11, pair=(17,27), p=17, n mod 27 in {0,16} | d=23, pair=(38,54), p=19, n mod 27 in {0,4} | d=35, pair=(54,86), p=43, n mod 27 in {0,19} | d=35, pair=(27,113), p=113, n mod 27 in {0,19} | d=47, pair=(54,134), p=67, n mod 27 in {0,7} | d=71, pair=(68,216), p=17, n mod 27 in {0,10}`

### extra moduli `32`

- rules seen: `8`
- rules passed: `8`
- support count: `7121`
- examples: `d=31, pair=(32,92), p=23, n mod 32 in {0,1} | d=55, pair=(32,188), p=47, n mod 32 in {0,9} | d=39, pair=(32,124), p=31, n mod 32 in {0,25} | d=79, pair=(32,284), p=71, n mod 32 in {0,17} | d=119, pair=(32,444), p=37, n mod 32 in {0,9} | d=87, pair=(32,316), p=79, n mod 32 in {0,9}`

### extra moduli `23`

- rules seen: `5`
- rules passed: `5`
- support count: `3461`
- examples: `d=15, pair=(23,37), p=37, n mod 23 in {0,8} | d=19, pair=(23,53), p=53, n mod 23 in {0,4} | d=27, pair=(46,62), p=31, n mod 23 in {0,19} | d=51, pair=(46,158), p=79, n mod 23 in {0,18} | d=31, pair=(23,101), p=101, n mod 23 in {0,15}`

### extra moduli `25`

- rules seen: `8`
- rules passed: `8`
- support count: `2985`
- examples: `d=31, pair=(50,74), p=37, n mod 25 in {0,19} | d=59, pair=(50,186), p=31, n mod 25 in {0,16} | d=39, pair=(50,106), p=53, n mod 25 in {0,11} | d=39, pair=(25,131), p=131, n mod 25 in {0,11} | d=59, pair=(86,150), p=43, n mod 25 in {0,16} | d=111, pair=(100,344), p=43, n mod 25 in {0,14}`

### extra moduli `17`

- rules seen: `8`
- rules passed: `8`
- support count: `2908`
- examples: `d=15, pair=(17,43), p=43, n mod 17 in {0,2} | d=19, pair=(17,59), p=59, n mod 17 in {0,15} | d=35, pair=(38,102), p=19, n mod 17 in {0,16} | d=27, pair=(34,74), p=37, n mod 17 in {0,7} | d=35, pair=(17,123), p=41, n mod 17 in {0,16} | d=63, pair=(68,184), p=23, n mod 17 in {0,5}`

### extra moduli `5;7`

- rules seen: `5`
- rules passed: `5`
- support count: `2278`
- examples: `d=19, pair=(35,41), p=41, n mod 5 in {0,1} AND n mod 7 in {0,2} | d=31, pair=(35,89), p=89, n mod 5 in {0,4} AND n mod 7 in {0,4} | d=59, pair=(21,215), p=43, n mod 5 in {0,1} AND n mod 7 in {0,4} | d=59, pair=(70,166), p=83, n mod 5 in {0,1} AND n mod 7 in {0,4} | d=59, pair=(35,201), p=67, n mod 5 in {0,1} AND n mod 7 in {0,4}`

### extra moduli `19`

- rules seen: `6`
- rules passed: `6`
- support count: `1668`
- examples: `d=15, pair=(19,41), p=41, n mod 19 in {0,4} | d=31, pair=(38,86), p=43, n mod 19 in {0,7} | d=23, pair=(19,73), p=73, n mod 19 in {0,15} | d=35, pair=(57,83), p=83, n mod 19 in {0,3} | d=27, pair=(19,89), p=89, n mod 19 in {0,11} | d=51, pair=(38,166), p=83, n mod 19 in {0,6}`

### extra moduli `9;5`

- rules seen: `5`
- rules passed: `5`
- support count: `1534`
- examples: `d=71, pair=(5,279), p=31, n mod 9 in {0,1} AND n mod 5 in {0,4} | d=59, pair=(90,146), p=73, n mod 9 in {0,4} AND n mod 5 in {0,1} | d=59, pair=(45,191), p=191, n mod 9 in {0,4} AND n mod 5 in {0,1} | d=119, pair=(180,296), p=37, n mod 9 in {0,7} AND n mod 5 in {0,1} | d=71, pair=(90,194), p=97, n mod 9 in {0,1} AND n mod 5 in {0,4}`

### extra moduli `64`

- rules seen: `3`
- rules passed: `3`
- support count: `1318`
- examples: `d=39, pair=(64,92), p=23, n mod 64 in {0,25} | d=63, pair=(64,188), p=47, n mod 64 in {0,1} | d=87, pair=(64,284), p=71, n mod 64 in {0,41}`

### extra moduli `31`

- rules seen: `3`
- rules passed: `3`
- support count: `1134`
- examples: `d=23, pair=(31,61), p=61, n mod 31 in {0,8} | d=35, pair=(47,93), p=47, n mod 31 in {0,27} | d=51, pair=(62,142), p=71, n mod 31 in {0,11}`

### extra moduli `29`

- rules seen: `4`
- rules passed: `4`
- support count: `1132`
- examples: `d=19, pair=(29,47), p=47, n mod 29 in {0,10} | d=35, pair=(29,111), p=37, n mod 29 in {0,23} | d=27, pair=(29,79), p=79, n mod 29 in {0,2} | d=35, pair=(58,82), p=41, n mod 29 in {0,23}`

### extra moduli `5;11`

- rules seen: `2`
- rules passed: `2`
- support count: `1072`
- examples: `d=39, pair=(46,110), p=23, n mod 5 in {0,1} AND n mod 11 in {0,5} | d=39, pair=(55,101), p=101, n mod 5 in {0,1} AND n mod 11 in {0,5}`

### extra moduli `11;13`

- rules seen: `1`
- rules passed: `1`
- support count: `951`
- examples: `d=43, pair=(29,143), p=29, n mod 11 in {0,1} AND n mod 13 in {0,9}`

### extra moduli `16;5`

- rules seen: `3`
- rules passed: `3`
- support count: `830`
- examples: `d=119, pair=(16,460), p=23, n mod 16 in {0,9} AND n mod 5 in {0,1} | d=79, pair=(80,236), p=59, n mod 16 in {0,1} AND n mod 5 in {0,1} | d=159, pair=(16,620), p=31, n mod 16 in {0,1} AND n mod 5 in {0,1}`

### extra moduli `7;11`

- rules seen: `2`
- rules passed: `2`
- support count: `759`
- examples: `d=87, pair=(7,341), p=31, n mod 7 in {0,4} AND n mod 11 in {0,1} | d=83, pair=(66,266), p=19, n mod 7 in {0,1} AND n mod 11 in {0,5}`

### extra moduli `7;13`

- rules seen: `2`
- rules passed: `2`
- support count: `629`
- examples: `d=75, pair=(13,287), p=41, n mod 7 in {0,2} AND n mod 13 in {0,3} | d=75, pair=(118,182), p=59, n mod 7 in {0,2} AND n mod 13 in {0,3}`

### extra moduli `128`

- rules seen: `2`
- rules passed: `2`
- support count: `557`
- examples: `d=55, pair=(92,128), p=23, n mod 128 in {0,73} | d=79, pair=(128,188), p=47, n mod 128 in {0,49}`

### extra moduli `47`

- rules seen: `2`
- rules passed: `2`
- support count: `534`
- examples: `d=27, pair=(47,61), p=61, n mod 47 in {0,20} | d=39, pair=(47,109), p=109, n mod 47 in {0,8}`

### extra moduli `9;7`

- rules seen: `2`
- rules passed: `2`
- support count: `424`
- examples: `d=59, pair=(63,173), p=173, n mod 9 in {0,4} AND n mod 7 in {0,4} | d=143, pair=(14,558), p=31, n mod 9 in {0,1} AND n mod 7 in {0,4}`

## Interpretation

The clean next mathematical target is now visible: prove a general
compound lemma that takes the dominant-prime condition plus the local
sets for a small list of extra prime powers.  This replaces explicit
lift enumeration with small modular hypotheses.

Verdict: not proved yet.
