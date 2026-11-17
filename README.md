# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/adityapramana24-creator/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/adityapramana24-creator/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecaster for make.fun's `gta6-twitch-ccu-forecast-01` bounty: predict
Twitch concurrent viewers in the "Grand Theft Auto VI" category for hours
2–24 of release day (19 Nov 2026 UTC), as five quantiles per hour
(0.05/0.25/0.5/0.75/0.95), scored by mean pinball loss on the log scale.
Pure Python 3.13, stdlib only, offline, deterministic, ~0.04 s per case.

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
   through the day (slope ≈ 0 at hour 2, −0.66 by hour 24). One pooled
   regression fits a slope linear in hour, b_h = b0 + b1·(h−13)/11, and
   each comparable's log-ratios are adjusted by it.
4. **Quantiles.** Per hour, the forecast is the median of the adjusted
   log-ratios plus the target's own slope shift, with a normal spread from
   the adjusted ratios' sample standard deviation.

## Validation

Tuning set: leave-one-comparable-out (LOCO) over the 17-member reference
class. Holdout: the practice cases, checked once after selection.

| | LOCO (17 targets) | Holdout (4 cases) |
|---|---|---|
| This model | **0.270** | **0.165** |
| Persistence baseline | 0.387 | 0.387 |

LOCO: 14/17 paired wins, 90% coverage 0.88 (baseline 0.75), typical miss
53% (baseline 78%). Holdout per case: Wolverine 0.171 vs 0.744, RDR2
0.162 vs 0.287, God of War Ragnarök 0.138 vs 0.215, Spider-Man 2 0.190 vs
0.303. The model beats the baseline at 22 of 23 hours (it loses only at
hour 6, the US-East unlock hour, by 0.004) and in all three regimes
(flat/mid/steep launches). Calibration: the local scorer reproduces the
house's stated starter numbers exactly on all four practice cases (loss
0.387, typical miss 82.7%, 90% coverage 0.783), so the local scores are
on the server's scale.

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
