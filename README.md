# Исследование гипотезы Эрдёша-Штрауса

Это небольшой Python-проект для экспериментов с гипотезой Эрдёша-Штрауса.

Статус проекта: исследовательский инструмент. Гипотеза здесь не доказана.
Репозиторий содержит код, компактные отчёты и небольшие CSV-снимки; большие
генерируемые таблицы намеренно не хранятся в git.

## Структура репозитория

- `erdos_straus.py` — основной solver и CSV exporter.
- `*.py` в корне — исследовательские скрипты для residue search, symbolic
  cover, family lemmas и диагностики.
- `reports/` — компактные отчёты и lemma candidates.
- `data/` — небольшие CSV-снимки результатов.
- `docs/PROJECT_STRUCTURE.md` — пояснение структуры и guardrails.

Гипотеза говорит, что для каждого целого `n >= 2` можно найти положительные
целые числа `x`, `y`, `z`, такие что:

```text
4/n = 1/x + 1/y + 1/z
```

То есть дробь `4/n` должна раскладываться в сумму трех единичных дробей.

## Готовые формулы

Некоторые классы чисел `n` покрываются простыми формулами.

### Четные n

Если `n` четное, то:

```text
4/n = 1/(n/2) + 1/n + 1/n
```

Пример для `n = 10`:

```text
4/10 = 1/5 + 1/10 + 1/10
```

### n, кратные 3

Если `n = 3k`, то:

```text
4/n = 1/(n/3) + 1/(2n) + 1/(2n)
```

Пример для `n = 9`:

```text
4/9 = 1/3 + 1/18 + 1/18
```

### n == 3 mod 4

Если `n` дает остаток `3` при делении на `4`, то:

```text
4/n = 1/((n+1)/4) + 1/(n(n+1)/2) + 1/(n(n+1)/2)
```

Пример для `n = 7`:

```text
4/7 = 1/2 + 1/28 + 1/28
```

## Brute force

Если число `n` не покрывается готовыми формулами, программа запускает
перебор. Она перебирает `x` и `y`, а `z` вычисляет из остатка:

```text
4/n - 1/x - 1/y = 1/z
```

Проверка решений выполняется через `fractions.Fraction`, поэтому нет ошибок
округления, которые бывают при использовании `float`.

Важно: brute force не является доказательством гипотезы. Он только помогает
находить конкретные решения и смотреть на паттерны в числах, которые не
покрылись простыми формулами.

## Research stage: from brute force to residue-class proof

После первых экспериментов проект перешел от ручных формул к общей схеме,
которую мы называем `general key d`.

Берем:

```text
x = (n+d)/4
```

Это можно делать только когда `n+d` делится на `4`. Тогда:

```text
1/x = 4/(n+d)
```

Остаток равен:

```text
4/n - 1/x
= 4/n - 4/(n+d)
= 4d / (n(n+d))
```

Теперь нужно представить этот остаток как сумму двух единичных дробей. Если
есть числа `a` и `b`, такие что:

```text
a + b = 4d
```

и `N = n(n+d)` делится на `a` и на `b`, то:

```text
y = N/a
z = N/b
```

и:

```text
1/y + 1/z = a/N + b/N = (a+b)/N = 4d/N
```

Первые найденные ключи `d=3,7,11` соответствуют:

```text
x = (n+3)/4
x = (n+7)/4
x = (n+11)/4
```

Они не являются отдельными чудесами, а просто первые случаи общей схемы.

Важно различать три уровня результата:

- `verified up to N`: компьютер проверил все `n` до некоторой границы `N`;
- `proven residue classes`: формулы покрывают целые классы остатков, например
  все `n == r mod L`;
- `conjectural pattern`: паттерн выглядит многообещающе, но еще не является
  доказательством.

Brute force и проверка до большого `N` не доказывают гипотезу для всех `n`.
Для доказательного шага нужен контроль бесконечных классов остатков.

## Запуск

Проверить все `n` от `2` до `300`:

```bash
python erdos_straus.py --max-n 300 --max-d 200
```

Проверить большой диапазон с поиском general keys:

```bash
python erdos_straus.py --max-n 100000 --max-d 2000
```

Записать CSV в другой файл:

```bash
python erdos_straus.py --max-n 300 --max-d 200 --csv my_results.csv
```

По умолчанию результаты записываются в `results.csv`.

CSV-колонки:

```text
n,method,x,y,z,verified,d,a,b,n_mod_4,n_mod_8,n_mod_12,n_mod_24,n_mod_60,n_mod_120,n_mod_840
```

Анализ CSV:

```bash
python analyze_patterns.py
```

Поиск покрытия по классам остатков:

```bash
python prove_by_residues.py --modulus 840 --max-d 500 --search-cover
python prove_by_residues.py --modulus 2520 --max-d 1000 --search-cover
python prove_by_residues.py --modulus 5040 --max-d 2000 --search-cover
```

Диагностика непокрытых классов:

```bash
python diagnose_uncovered.py --modulus 840 --max-d 5000
python diagnose_uncovered.py --modulus 2520 --max-d 5000
python diagnose_uncovered.py --modulus 5040 --max-d 5000
```

Lifted proof search дробит непокрытые классы на подклассы с более точным
модулем:

```bash
python prove_by_residues.py --modulus 840 --max-d 5000 --search-cover --lift-uncovered
python prove_by_residues.py --modulus 2520 --max-d 5000 --search-cover --lift-uncovered
python prove_by_residues.py --modulus 5040 --max-d 5000 --search-cover --lift-uncovered
```

Focused attack on `n == 1 mod 24`:

```bash
python attack_1_mod_24.py --max-n 500000 --max-d 5000
python attack_1_mod_24.py --modulus-search --max-d 5000
python attack_1_mod_24.py --greedy-cover --max-d 5000
```

## Family-lemma search by prime factors

После symbolic/remainder этапов полезнее искать не новые большие деревья
перебора, а короткие семейные леммы для правил `(d,a,b)`.

Для фиксированного правила достаточно проверять простые степени из:

```text
q = lcm(4,a,b)
```

Если один простой множитель `p` доминирует, часто правило на hard core
`n == 1 mod 24` сводится к условию:

```text
n mod p in {0, -d}
```

Чистые семейства:

```text
F1: a=1,  b=p,   p=4d-1
F2: a=2,  b=2p,  p=2d-1
F3: a=3,  b=p,   p=4d-3
F4: a=6,  b=2p,  p=2d-3
F5: a=24, b=4p,  p=d-6
```

Запуски:

```bash
python prime_factor_family_lemma_finder.py
python automatic_small_factor_lemma_finder.py
python parametric_family_lemma_tester.py --max-d 20000
python compound_factor_family_lemma_finder.py
python compound_symbolic_cover.py --focus-residue 289 --max-family-rules 20 --summary-only
python family_negative_implication_finder.py --sample-limit 200 --max-family-rules 30 --candidate-limit 8 --max-ratio 50000 --search-depth 6
python family_negative_obstruction_analyzer.py
python prime_set_cover_lemma_finder.py --max-rules 120 --max-prime-set-size 4 --max-modulus 250000
```

Смысл результатов:

- `prime_factor_family_lemma_finder.py` проверяет разложение правила на
  локальные условия по простым степеням;
- `automatic_small_factor_lemma_finder.py` ищет правила, где все малые
  множители автоматические на `n == 1 mod 24`;
- `parametric_family_lemma_tester.py` проверяет чистые семейства `F1`-`F5`;
- `compound_factor_family_lemma_finder.py` группирует оставшиеся правила по
  дополнительным малым условиям, например modulo `5`, `7`, `9`, `16`.
- `compound_symbolic_cover.py` применяет эти семейные условия к symbolic
  remainders через CRT и сохраняет compact remainder вида
  `base class AND NOT(family conditions)`.
- `family_negative_implication_finder.py` ищет леммы вида
  `Base AND NOT(A1) AND ... AND NOT(Ak) => B`.
- `family_negative_obstruction_analyzer.py` объясняет, почему прямой forcing
  часто не появляется: target-правило приносит новый простой модуль, независимый
  от уже накопленных отрицаний.
- `prime_set_cover_lemma_finder.py` группирует правила по общим простым
  модулям и проверяет малые fixed-prime universes, где target-prime уже не
  является свежим.

Это всё еще не доказательство гипотезы. Это способ заменить взрывающиеся
lift-деревья маленькими читаемыми условиями на остатки.

Отчёты по этому этапу лежат в `reports/`. Начать удобно с:

```text
reports/INDEX.md
reports/compound_symbolic_cover_report.md
reports/family_negative_obstruction_report.md
reports/prime_set_cover_lemma_report.md
```

Можно отдельно включить редукцию через делители:

```bash
python attack_1_mod_24.py --max-n 500000 --max-d 5000 --reduce-by-divisors
```

Идея редукции простая. Если для `m` есть решение:

```text
4/m = 1/x + 1/y + 1/z
```

то для любого кратного `n = k*m` есть решение:

```text
4/n = 1/(kx) + 1/(ky) + 1/(kz)
```

Поэтому если `n` имеет меньший делитель `m > 1`, который уже покрыт
формулами, то `n` тоже покрыто. Самые важные трудные случаи после такой
редукции — числа без полезных малых делителей, особенно простые числа или
числа, взаимно простые с базовыми модулями.

`prove_by_residues.py` специально осторожен: он не создает
`proof_certificate.md`, если есть непокрытые остатки или если sample-проверки
формул не прошли. Даже если сертификат создан, это компьютерно найденный
кандидат на доказательство, который нужно независимо проверить математически.
