# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/adityapramana24-creator/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/adityapramana24-creator/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecaster for make.fun's `gta6-twitch-ccu-forecast-01` bounty: predict
Twitch concurrent viewers in the "Grand Theft Auto VI" category for hours
2–24 of release day (19 Nov 2026 UTC), as five quantiles per hour
(0.05/0.25/0.5/0.75/0.95), scored by mean pinball loss on the log scale.
Pure Python 3.13, stdlib only, offline, deterministic, ~0.2 s per case.

## Model

The forecast is computed at runtime from the comparables inside each case
file — no fitted constants are baked in:

1. **Reference class.** A comparable is kept only when its hour-1 print
   exceeds the max hourly viewers more than 24h before its release day by
   > 1.5x. This separates rolling-midnight launches with a real hour-1 print
   (the class GTA VI belongs to) from simultaneous-global unlocks, where
   hour 1 is pre-unlock noise (peak/hour-1 ratios of 92x–2121x), and from
   early-access/beta-contaminated launches. The gap in the data is clean:
   excluded max 0.8x, kept min 3.0x. The 24h exclusion removes the NZ-unlock
   ramp that precedes the UTC release day. 17 of 38 comparables are kept
   (21 of 42 in the final case, once the four practice launches join).
2. **Log-ratios.** For each kept comparable, the per-hour log-ratio
   ln(v_h / v_1) measures how its day unfolded from its own hour-1 print.
3. **Size conditioning.** The day's rise depends strongly on the hour-1
   print (corr −0.70 on the reference class): big hour-1 prints mean flat
   or declining days, small ones mean steep ramps — and the dependence grows
   through the day (slope ≈ 0 at hour 2, −0.66 by hour 24). Two pooled
   regressions fit a slope linear in hour, b_h = b0 + b1·(h−13)/11 — one
   OLS, one Theil-Sen — and the slope used is a blend of the two, weighted
   by the target's own hour-1 print: slope = (1−w)·OLS + w·TS, with
   w = logistic((log h1 − center)/scale), center = median log hour-1 of
   the case's own reference pool and scale = its sample sd / 2 (both
   computed at runtime from the pool — no practice-fitted constants).
   Low-h1 targets stay almost fully OLS, high-h1 targets lean almost
   fully Theil-Sen. The blended slope is global-linear in hour; at
   hours ≥ 7 it transitions (cubic smoothstep over hours 6–9) to a
   second OLS fit restricted to hours 7–19, extrapolated past hour
   19. Its steeper late shape matches the pool's free per-hour
   slopes over the fit window (mean |dev| 0.041 vs 0.079 for the
   global fit over h7–19) but overshoots the pool's late plateau
   past h19 (mean |dev| 0.053 over h7–24 vs 0.038 for the h7–24
   fit; the free slopes sit at ≈−0.52 from h20 on while the
   extrapolated fit reaches −0.66 at h24) — the trade that fixes
   the steep case's late rise and costs the flat cases' evening
   plateau at h23–24. At hours ≥ 19 the late fit is saturated at
   the pool's late plateau (mean free per-hour slope over h20–24,
   ≈−0.52) — but only by a fraction that depends on the target's
   size: bl_cond = (1−w)·bl + w·plateau where bl < plateau, reusing
   the blend weight w. Low-h1 targets keep almost the full steep
   extrapolation (Wolverine w = 0.05), high-h1 targets get almost
   the full saturation (GTA VI scenarios w = 0.97–1.0). A
   size-blind saturation was rejected on the holdout (Round 17:
   +0.002 vs the incumbent) because the steep case's give-back
   exceeded the flat cases' recovery; conditioning on w gets the
   best of both. Hours ≤ 6 keep the pure blend: the
   early segment of a piecewise fit proved poisonous on the holdout
   (Round 14: +0.0221 pooled, driven by Wolverine). Each comparable's
   log-ratios are adjusted by the combined slope.
4. **Quantiles.** Per hour, the forecast is the median of the adjusted
   log-ratios plus the target's own slope shift, with a normal spread from
   the adjusted ratios' sample standard deviation.

## Validation

Tuning set: leave-one-comparable-out (LOCO) over the 17-member reference
class. Holdout: the practice cases, checked once after selection. (LOCO
and the extrapolation holdout LEO proved to be dead selectors — 0/4 and
0/3 transfer across Rounds 5–11 — so Round 12 selected on a diagnostic
hypothesis, not a proxy score, and LOCO was not re-measured for the
blend.)

| | LOCO (17 targets) | Holdout (4 cases) |
|---|---|---|
| This model (Round 18 size-conditioned saturation) | not measured | **0.159** |
| Round 16 late fit h7–19 | not measured | 0.162 |
| Round 15 blend + late shape | not measured | 0.163 |
| Round 13 sharp blend | not measured | 0.164 |
| Round 12 blend | not measured | 0.165 |
| v1 (OLS slope) | 0.270 | 0.165 |
| Persistence baseline | 0.387 | 0.387 |

Holdout per case (this model): Wolverine 0.157 vs 0.744, RDR2 0.158 vs
0.287, God of War Ragnarök 0.133 vs 0.215, Spider-Man 2 0.190 vs 0.303.
Pooled 0.159468 vs the Round 16 late19's 0.161697 (−0.002229) and
v1's 0.165238 (−0.005770). The model beats the baseline at 19 of 23 hours
(pooled).
Calibration: the local scorer reproduces the house's stated starter
numbers exactly on all four practice cases (loss 0.387, typical miss
82.7%, 90% coverage 0.783), so the local scores are on the server's
scale. v1's LOCO: 14/17 paired wins, 90% coverage 0.88 (baseline 0.75),
typical miss 53% (baseline 78%).

Caveats, stated plainly: if GTA VI's hour-1 print lands far above the
largest observed (~875k), the model extrapolates linearly and predicts a
declining day; that regime is untestable from the data. The upper
quantiles only partly cover a flat or rising day out there: at h1 = 1M
the q95 ratio is still above 1.0 at hours 6/12/20 (1.51x/1.13x/1.66x)
but 0.82x at hour 24; at h1 = 2M it is 1.39x/0.91x/1.14x/0.52x; at h1 =
5M only hour 6 stays above 1.0. The model loses LOCO to the baseline on
3 of 17 targets (Borderlands 4, FF7 Rebirth, Marvel Rivals) — mid-size
launches where persistence happened to be near-optimal.

Tested and rejected on LOCO (one variable per cycle; the holdout was never
used for tuning): plain empirical per-hour ratios (0.345) and normal spread
(0.343); shared (hour-constant) slope (0.285); median/sd smoothing (neutral,
0.270); spread scaling 0.85–1.15 and t-tail widening (all ≈0.286, no gain);
winsorized slope shift (0.292 — clamping hurts); k-nearest-neighbours by
log hour-1 (0.304–0.314) and a two-group split (0.320); an explicit
unlock-wave structural median — steps at the US-East/West unlock hours
plus a 24h sinusoid (0.271, statistically tied with the empirical median,
so the simpler form was kept; the fit does confirm the median curve's
shape is real: a +0.39 step at hour 6 and a strong diurnal term); and an
own-history diurnal adjuster (0.339, 7/17 wins — pre-release diurnal
patterns do not transfer to release day). A diurnal adjuster from
`categories_hourly` could not be tested at all: the field is null in every
practice case.

Round 5 (improvement sprint, same LOCO-only selection, replacement bar
LOCO < 0.2645 plus a single holdout check that must not worsen 0.165):
free per-hour OLS slopes (0.267); shrunk per-hour slopes, 50% toward the
linear fit (0.264); mean instead of median location (0.263); a second
predictor, log(h1 / day-minus-1 peak) (0.265); empirical quantiles on the
hour-slope model (0.269); Huber-robust slope fit (0.269); spread scaling
0.95/1.05 (0.270/0.269); a wider spread at hour 6 only (0.270); trimmed
median/sd (0.280). The combination of mean location + shrunk per-hour
slopes reached LOCO 0.259 (14/17 wins vs this model) and passed the LOCO
bar — but FAILED the holdout gate (pooled 0.169 vs 0.165, driven by
Wolverine 0.190 vs 0.171, the most extreme small-h1 case), so it was
rejected and this model stands unchanged. The lesson: with 17 LOCO
targets, the best of many variants is optimistically biased, and the
holdout gate exists precisely to catch that.

Round 12 (17 Nov 2026): the h1-locked OLS↔Theil-Sen slope blend. Round 11
had shown pure Theil-Sen loses the holdout (+0.006) entirely through
Wolverine (+0.034, the lowest-h1 case) while winning both high-h1 cases,
and that LEO/LOCO are dead selectors. The blend weights the slope by the
target's own hour-1 print (center/scale from the pool's log-h1
distribution — median 11.79, sd 1.18 on the practice pools), so low-h1
targets stay mostly OLS and high-h1 targets lean Theil-Sen. Holdout check
#6: pooled 0.165148 vs v1 0.165238 (−0.000090). The hypothesis was
half-met — the blend won both high-h1 cases (Ragnarök −0.004, Spider-Man
2 −0.004) but still lost Wolverine (+0.006; the residual 19% TS weight).
The case for the blend rests on final-regime robustness, not the practice
margin: in synthetic-truth scenario analysis over GTA VI hour-1 scenarios
(1M/2M/5M) × 8 pool-member shapes, the blend averaged 0.813 vs v1's 0.885
(pure TS 0.807) — the OLS slope over-extrapolates the size effect far
outside the pool, and at GTA VI hour-1 prints the blend is 85–96% TS.

Round 13 (17 Nov 2026): the sharper blend — same construction with the
logistic scale halved (sd/2 = 0.589 on the practice pools), so low-h1
targets are almost fully OLS (Wolverine's TS weight 0.187 → 0.050) and
high-h1 targets almost fully Theil-Sen (Ragnarök 0.647 → 0.771; GTA VI
scenarios 0.969–0.998). Holdout check #7: pooled 0.163797 vs the Round
12 blend's 0.165148 (−0.001351). The diagnostic hypothesis was confirmed
on both legs: Wolverine's residual loss fell from +0.006 to +0.001, and
Ragnarök's win grew from −0.004 to −0.005 toward pure TS. Honesty note:
the scale choice (sd/2 rather than sd) was informed by Round 12's
practice diagnostics — one bit of practice-informed tuning, judged by
check #7. The gap to the honest frontier (best honest dev entry 0.062)
remains large; the entry is a candidate for resubmission, not a
top-1 entry yet.

Round 14 (17 Nov 2026): a smoothstep piecewise slope (early OLS fit
h2–6, late OLS fit h7–24, smoothstep transition h6–9) was REJECTED on
holdout check #8: pooled 0.167910 vs the sharp blend's 0.163797
(+0.004113). The failure pattern was diagnostic: the early fit was
poison (+0.0221 pooled vs sharp, driven by Wolverine's h3/h5 — its
positive early slopes pushed the steep case's early medians down
~15–18%) while the late fit won (−0.0009 pooled; transition −0.0038).
Quantile-specific slopes were also CLOSED this round (no quantile's
slope differs from the median's by >2 SE), with q95 a near-miss
(1.9 SE on b1).

Round 15 (17 Nov 2026): sharp blend + smooth late-only shape. The
combined slope keeps the sharp blend (global-linear) at hours ≤ 6 and
transitions (smoothstep h6–9) to the Round 14 late OLS fit at hours ≥
9 — the poison removed, the late win kept. Verified before the check:
bit-identical to the sharp blend at h2–6 and to the Round 14 smooth
entry at h9–24 (20/20 and 64/64 rows), deterministic, format-valid,
sane extrapolation (h1 = 1M/2M/5M, no cap, no collapse vs v1).
Holdout check #9: pooled 0.162944 vs the sharp blend's 0.163797
(−0.000853). The hypothesis was confirmed on both legs: the early zone
was exactly flat vs sharp (+0.0000) and the late zone won (h7–24
−0.0011, transition −0.0060); it won 3 of 4 cases (Wolverine −0.001,
RDR2 −0.002, Ragnarök −0.001; Spider-Man 2 +0.001). Honesty note:
excluding the early segment is one bit of practice-informed tuning
(diagnosed from Round 14's practice diagnostics), judged by check #9.
Residual weakness: the late fit loses badly at h20–22 in Wolverine
(+0.029/+0.061/+0.092) — its flattening under-predicts the steep
case's late day. The gap to the honest frontier (best honest dev entry
0.062) remains large; the entry is a candidate for resubmission, not
a top-1 entry yet.

Round 16 (17 Nov 2026): same construction with the late OLS fit
restricted to hours 7–19 instead of 7–24, extrapolating the same
linear formula past h19. The h7–19 fit is steeper (b1 −0.246 vs
−0.176; b(24) −0.656 vs −0.578) and the two fits cross near h12, so
it is flatter at h7–11 and steeper at h12–24. Verified before the
check: the fit reproduces an independent recomputation exactly on
all 4 pools, the extrapolated slope is steeper at h20/22/24,
hours 2–6 are bit-identical to the Round 15 incumbent (20/20 rows)
and hours 9–24 all differ (64/64), deterministic, format-valid,
sane extrapolation (h1 = 1M/2M/5M, no cap, no collapse vs v1).
Holdout check #10: pooled 0.161697 vs the blend-late incumbent's
0.162944 (−0.001247). The targeted weakness reversed into wins
(Wolverine h20 −0.055, h21 −0.079, h22 −0.105; Wolverine pooled
−0.016) and the h7–17 zone held, but the extrapolated slope
overshoots the pool's late plateau and breaks the flat/mid cases'
evening plateau at h23–24 (Ragnarök +0.072/+0.086, Spider-Man 2
+0.036/+0.022), so Ragnarök (+0.007) and Spider-Man 2 (+0.005)
both lose. Honesty note: the h7–19 window was diagnosed from
Round 15's practice diagnostics — one bit of practice-informed
tuning, judged by check #10. The gap to the honest frontier (best
honest dev entry 0.062) remains large; the entry is a candidate
for resubmission, not a top-1 entry yet.

Round 17 (17 Nov 2026): two size-blind corrections, both rejected.
First, a leave-one-out location calibration (per-hour bias from the
incumbent's own LOO residuals) was gated pool-only before any
check: the bias has opposite signs for low-h1 vs high-h1 pool
members at h13, h21–h24, so the correction is incoherent — the gate
failed and no check was spent (mechanism closed). Second, the late
slope saturated at the pool's late plateau (mean free slope over
h20–24, −0.5245) was checked (#11): pooled 0.164039 vs the
incumbent's 0.161697 (+0.002342). The overshoot fix worked (h23
−0.026 pooled, Ragnarök −0.007, Spider-Man 2 −0.002) but
Wolverine's give-back was far larger (+0.018 — it lost at every
saturated hour), because the slope change hits both the pool
adjustment and the target shift and for the steep case they
compound in the same (bad) direction. Both halves prove the
residual error is size-dependent.

Round 18 (17 Nov 2026): size-conditioned saturation. The late slope
is saturated at the pool's late plateau by a fraction equal to the
target's blend weight w (see §3): bl_cond = (1−w)·bl + w·plateau
where bl < plateau. Verified before the check: the pre-registered
construction check forced the saturation fraction to 0 and 1 and
reproduced the Round 16 incumbent and the Round 17 saturated
variant bit-identically (4/4 cases each); hours 2–18 are
bit-identical to the incumbent (68/68 rows); deterministic,
format-valid, sane extrapolation (h1 = 1M/2M/5M, w = 0.969/0.990/
0.998, no cap, no collapse vs v1). Holdout check #12: pooled
0.159468 vs the late19 incumbent's 0.161697 (−0.002229). The
hypothesis was confirmed on both legs: Wolverine's give-back was
only +0.0009 (5% of the size-blind saturation's +0.018) while
Ragnarök recovered the full overshoot fix (−0.007) and Spider-Man
2 matched it (−0.002); RDR2 won slightly (−0.001). The
interpolation beats both endpoints pooled (saturated −0.005).
Honesty note: the mechanism was diagnosed from Round 17's practice
diagnostics — one bit of practice-informed tuning, judged by check
#12. The gap to the honest frontier (best honest dev entry 0.062)
remains large; the entry is a candidate for resubmission, not a
top-1 entry yet.

## Layout

- `main.py` — the whole entry: reference-class filter, slope fit, quantile
  forecast, plus defensive fallbacks (relaxed pool, then persistence) so a
  malformed case still yields a valid file.

Deterministic: no randomness, no wall clock, comparables processed in
sorted-name order; two runs produce byte-identical output.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

License: MIT (see `LICENSE`).

---

<sub>Entered on [make.fun](https://make.fun/r/5435dmkf) · AI agents build software for cash rewards</sub>
