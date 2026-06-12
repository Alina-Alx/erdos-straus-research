# Prime-Set Cover Lemma Report

This report groups family rules by shared prime moduli and tests small
fixed-prime universes. The goal is to avoid the previous obstruction
where a target rule introduced a fresh independent prime.

This is a finite diagnostic over selected rule families, not a proof
of the full Erdős-Straus conjecture.

## Prime Support

- top condition primes by rule support: `[(5, 67589), (43, 65109), (23, 59522), (31, 58549), (37, 57440), (41, 49188), (29, 48981), (17, 46326), (19, 31330), (53, 30932), (3, 29713), (59, 28517), (7, 25995), (61, 24576), (2, 18718)]`
- top missing primes from symbolic master keys: `[(43, 25262), (37, 23750), (23, 23670), (31, 23532), (41, 23064), (29, 21060), (17, 18525), (3, 15049), (59, 13729), (53, 13033), (19, 12250), (61, 10950), (47, 10575), (67, 7795), (89, 7617)]`

## Strongest Rule Groups

### exact_signature `43`

- rule count: `3`
- support count: `57697`
- examples: `d=11,a=1,b=43 | d=23,a=6,b=86 | d=87,a=4,b=344`

### exact_signature `41`

- rule count: `2`
- support count: `46650`
- examples: `d=11,a=3,b=41 | d=47,a=24,b=164`

### exact_signature `37`

- rule count: `2`
- support count: `45562`
- examples: `d=19,a=2,b=74 | d=39,a=8,b=148`

### exact_signature `23`

- rule count: `4`
- support count: `43568`
- examples: `d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=71,a=8,b=276`

### exact_signature `31`

- rule count: `4`
- support count: `31945`
- examples: `d=47,a=2,b=186 | d=31,a=62,b=62 | d=63,a=4,b=248 | d=95,a=8,b=372`

### exact_signature `29`

- rule count: `2`
- support count: `27637`
- examples: `d=15,a=2,b=58 | d=31,a=8,b=116`

### exact_signature `59`

- rule count: `2`
- support count: `26983`
- examples: `d=15,a=1,b=59 | d=119,a=4,b=472`

### exact_signature `19`

- rule count: `2`
- support count: `25440`
- examples: `d=11,a=6,b=38 | d=39,a=4,b=152`

### exact_signature `53`

- rule count: `2`
- support count: `24333`
- examples: `d=27,a=2,b=106 | d=55,a=8,b=212`

### exact_signature `61`

- rule count: `2`
- support count: `21781`
- examples: `d=31,a=2,b=122 | d=63,a=8,b=244`

### exact_signature `5;29`

- rule count: `2`
- support count: `18099`
- examples: `d=11,a=15,b=29 | d=39,a=40,b=116`

### exact_signature `17`

- rule count: `1`
- support count: `17832`
- examples: `d=23,a=24,b=68`

### exact_signature `89`

- rule count: `2`
- support count: `16049`
- examples: `d=23,a=3,b=89 | d=95,a=24,b=356`

### exact_signature `7;31`

- rule count: `1`
- support count: `15360`
- examples: `d=19,a=14,b=62`

### exact_signature `67`

- rule count: `1`
- support count: `13954`
- examples: `d=35,a=6,b=134`

### exact_signature `11;17`

- rule count: `1`
- support count: `13361`
- examples: `d=7,a=11,b=17`

### exact_signature `5;71`

- rule count: `1`
- support count: `11771`
- examples: `d=19,a=5,b=71`

### exact_signature `47`

- rule count: `4`
- support count: `11088`
- examples: `d=47,a=47,b=141 | d=71,a=2,b=282 | d=95,a=4,b=376 | d=143,a=8,b=564`

### exact_signature `107`

- rule count: `1`
- support count: `11080`
- examples: `d=27,a=1,b=107`

### exact_signature `5;31`

- rule count: `2`
- support count: `8157`
- examples: `d=39,a=1,b=155 | d=59,a=50,b=186`

## Best Small Fixed-Prime Cover Checks

### primes `17;19;23`

- status: `checked`
- modulus: `178296`
- rules: `7`
- covered residues: `2869/7429`
- coverage ratio: `0.386189`
- uncovered examples: `1;25;49;73;97;121;145;169;193;313;337;409;433;457;553;577;601;625;649;745`
- rule examples: `d=11,a=6,b=38 | d=23,a=24,b=68 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=39,a=4,b=152`

### primes `17;19;31`

- status: `checked`
- modulus: `240312`
- rules: `7`
- covered residues: `3533/10013`
- coverage ratio: `0.352841`
- uncovered examples: `1;25;49;73;97;121;145;169;193;241;313;337;409;457;481;505;529;553;577;601`
- rule examples: `d=11,a=6,b=38 | d=23,a=24,b=68 | d=47,a=2,b=186 | d=31,a=62,b=62 | d=63,a=4,b=248 | d=39,a=4,b=152 | d=95,a=8,b=372`

### primes `17;19;29`

- status: `checked`
- modulus: `224808`
- rules: `5`
- covered residues: `3127/9367`
- coverage ratio: `0.333832`
- uncovered examples: `1;25;49;73;97;121;169;193;241;313;337;409;457;481;505;529;553;577;601;625`
- rule examples: `d=11,a=6,b=38 | d=15,a=2,b=58 | d=23,a=24,b=68 | d=31,a=8,b=116 | d=39,a=4,b=152`

### primes `3;19;23`

- status: `checked`
- modulus: `94392`
- rules: `8`
- covered residues: `1273/3933`
- coverage ratio: `0.323671`
- uncovered examples: `1;25;49;73;97;121;145;169;193;289;313;337;385;409;433;457;553;577;601;625`
- rule examples: `d=11,a=6,b=38 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=39,a=4,b=152 | d=47,a=36,b=152 | d=23,a=38,b=54`

### primes `5;19;23`

- status: `checked`
- modulus: `52440`
- rules: `7`
- covered residues: `697/2185`
- coverage ratio: `0.318993`
- uncovered examples: `1;25;49;73;97;121;145;169;193;289;313;337;385;409;433;457;553;577;601;625`
- rule examples: `d=11,a=6,b=38 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=59,a=6,b=230 | d=39,a=4,b=152`

### primes `3;5;23;29`

- status: `checked`
- modulus: `240120`
- rules: `10`
- covered residues: `3063/10005`
- coverage ratio: `0.306147`
- uncovered examples: `1;25;49;73;97;121;169;193;265;289;313;337;361;385;409;457;553;577;601;625`
- rule examples: `d=15,a=2,b=58 | d=11,a=15,b=29 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=31,a=8,b=116 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=59,a=6,b=230 | d=47,a=72,b=116 | d=39,a=40,b=116`

### primes `5;17;23`

- status: `checked`
- modulus: `46920`
- rules: `7`
- covered residues: `596/1955`
- coverage ratio: `0.304859`
- uncovered examples: `1;25;49;73;97;121;145;169;193;217;265;313;337;361;409;433;457;553;577;601`
- rule examples: `d=23,a=24,b=68 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=39,a=20,b=136 | d=71,a=8,b=276 | d=59,a=6,b=230`

### primes `19;23`

- status: `checked`
- modulus: `10488`
- rules: `6`
- covered residues: `133/437`
- coverage ratio: `0.304348`
- uncovered examples: `1;25;49;73;97;121;145;169;193;289;313;337;385;409;433;457;553;577;601;625`
- rule examples: `d=11,a=6,b=38 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=39,a=4,b=152`

### primes `5;23;29`

- status: `checked`
- modulus: `80040`
- rules: `9`
- covered residues: `990/3335`
- coverage ratio: `0.296852`
- uncovered examples: `1;25;49;73;97;121;169;193;265;289;313;337;361;385;409;457;553;577;601;625`
- rule examples: `d=15,a=2,b=58 | d=11,a=15,b=29 | d=23,a=23,b=69 | d=35,a=2,b=138 | d=31,a=8,b=116 | d=47,a=4,b=184 | d=71,a=8,b=276 | d=59,a=6,b=230 | d=39,a=40,b=116`

### primes `3;19;31`

- status: `checked`
- modulus: `127224`
- rules: `9`
- covered residues: `1569/5301`
- coverage ratio: `0.295982`
- uncovered examples: `1;25;49;73;97;121;145;169;193;241;289;313;337;385;409;457;481;505;529;553`
- rule examples: `d=11,a=6,b=38 | d=47,a=2,b=186 | d=31,a=62,b=62 | d=63,a=4,b=248 | d=39,a=4,b=152 | d=95,a=8,b=372 | d=47,a=36,b=152 | d=23,a=38,b=54 | d=71,a=36,b=248`

## Lemma Direction

A promising family lemma should fix a small prime universe `P` and
only use rules whose condition primes are contained in `P`. Inside
that universe, target primes are not fresh; the obstruction from
`family_negative_obstruction_report.md` no longer applies.

A successful cover statement would have the form:

```text
For n == 1 mod 24 and residues modulo M(P), at least one rule
with prime_signature(rule) subset P applies.
```

The current finite checks are partial diagnostics. They do not prove
the conjecture.

Verdict: not proved yet.
