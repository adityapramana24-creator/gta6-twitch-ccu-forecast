"""Comparable-ratio forecaster for make.fun gta6-twitch-ccu-forecast-01.

Forecasts Twitch concurrent viewers in the release-day category for hours
2..24 as five log-scale quantiles per hour. The model is computed at runtime
from the comparables inside each case file (offline, stdlib only):

1. Reference class. A comparable is kept only when its hour-1 print exceeds
   the max hourly viewers more than 24h before its release day by > 1.5x.
   This separates rolling-midnight launches with a real hour-1 print (the
   class GTA VI belongs to) from simultaneous-global unlocks, where hour 1
   is pre-unlock noise, and from early-access/beta-contaminated launches.
   The gap in the data is clean (excluded max 0.8x, kept min 3.0x). The
   24h exclusion removes the NZ-unlock ramp that precedes the UTC day.
2. Log-ratios. For each kept comparable, the per-hour log-ratio
   ln(v_h / v_1) measures how its day unfolded from its own hour-1 print.
3. Size conditioning. The day's rise depends strongly on the hour-1 print
   (corr -0.70 on the reference class): big hour-1 prints mean flat or
   declining days, small ones mean steep ramps -- and the dependence grows
   through the day (near zero at hour 2, steep by hour 24). A single pooled
   regression fits one slope linear in hour, b_h = b0 + b1*(h-13)/11, and
   each comparable's log-ratios are adjusted by it.
4. Quantiles. Per hour, the forecast is the median of the adjusted
   log-ratios plus the target's own slope shift, with a normal spread from
   the adjusted ratios' sample standard deviation.

Validation (leave-one-comparable-out on the 17-member reference class):
mean pinball loss 0.270 vs 0.387 for the persistence baseline (-30%),
14/17 paired wins, 90% coverage 0.88, typical miss 53% (baseline 78%).
Practice holdout (all 4 cases, checked once after selection): pooled
0.165 vs 0.387 for the baseline (Wolverine 0.171, RDR2 0.162, God of War
Ragnarok 0.138, Spider-Man 2 0.190). The local scorer is fully calibrated:
the starter reproduces the house's stated numbers exactly (loss 0.387,
typical miss 82.7%, coverage 0.783).

Deterministic: no randomness, no wall clock, comparables processed in
sorted-name order so float summation is identical across runs.
"""

import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# Standard normal quantiles at the levels above.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Reference-class threshold: hour-1 print / pre-release max (>24h before
# the release day). Data gap is 0.8x (excluded) to 3.0x (kept).
KEEP_RATIO = 1.5
# Minimum reference-class size before the filter is relaxed.
MIN_POOL = 5
# Minimum pool size before falling back to persistence.
MIN_POOL_HARD = 3
# Spread floor (log units): only binds for degenerate pools.
SD_FLOOR = 0.05
# Persistence baseline spread (log units per sqrt hour), fallback only.
BASE_SPREAD = 0.15


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def comparable_day(comp):
    """Release-day curve {hour 1..24: viewers} and the max hourly viewers
    more than 24h before the release day, for one comparable."""
    day_start = parse_time(comp["day_start"])
    cutoff = day_start - timedelta(hours=24)
    curve = {}
    pre_max = 0
    for row in comp.get("hourly") or []:
        viewers = row.get("viewers")
        if viewers is None or viewers <= 0:
            continue
        try:
            when = parse_time(row["from"])
        except (KeyError, ValueError, TypeError):
            continue  # one malformed row must not kill the case
        if when < cutoff:
            if viewers > pre_max:
                pre_max = viewers
            continue
        hour = int((when - day_start).total_seconds() // 3600) + 1
        if 1 <= hour <= 24:
            curve[hour] = viewers
    return curve, pre_max


def reference_pool(case):
    """{name: curve} of comparables in the rolling-launch reference class.
    Falls back to all comparables with a usable curve if the class is too
    small, so the output is always produced."""
    usable = {}
    for comp in case.get("comparables") or []:
        curve, pre_max = comparable_day(comp)
        if 1 not in curve or len(curve) < 12:
            continue
        usable[comp["name"]] = (curve, pre_max)
    kept = {name: curve for name, (curve, pre_max) in usable.items()
            if pre_max > 0 and curve[1] / pre_max > KEEP_RATIO}
    if len(kept) >= MIN_POOL:
        return kept
    if len(usable) >= MIN_POOL_HARD:
        return {name: curve for name, (curve, _) in usable.items()}
    return {}


def hour_one_print(case):
    """Hour-1 viewers: the `known` print, else the day-start row of
    history_hourly, else 1 (with persistence fallback downstream)."""
    for row in case.get("known") or []:
        if row.get("hour") == 1 and row.get("viewers"):
            return float(row["viewers"])
    known = case.get("known") or []
    if known and known[0].get("viewers"):
        return float(known[0]["viewers"])
    try:
        day_start = parse_time(case["day_start"])
    except (KeyError, ValueError, TypeError):
        return 1.0
    for row in case.get("history_hourly") or []:
        try:
            when = parse_time(row["from"])
        except (KeyError, ValueError, TypeError):
            continue
        if row.get("viewers") and when == day_start:
            return float(row["viewers"])
    return 1.0


def quantile(sorted_vals, tau):
    """Linear-interpolation empirical quantile."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def fit_hour_slope(log_ratios, log_h1):
    """Pooled regression of hour-demeaned log-ratios on centered log hour-1
    prints, with the slope linear in hour: b_h = b0 + b1*(h-13)/11.
    Returns (b0, b1, center_log_h1)."""
    names = sorted(log_ratios)
    center = sum(log_h1[n] for n in names) / len(names)
    s00 = s01 = s11 = t0 = t1 = 0.0
    for h in range(2, 25):
        vals = {n: log_ratios[n][h] for n in names if h in log_ratios[n]}
        if len(vals) < 3:
            continue
        mean = sum(vals.values()) / len(vals)
        u = (h - 13) / 11.0
        for n, v in vals.items():
            x = log_h1[n] - center
            y = v - mean
            s00 += x * x
            s01 += x * x * u
            s11 += x * x * u * u
            t0 += x * y
            t1 += x * u * y
    det = s00 * s11 - s01 * s01
    if abs(det) < 1e-12:
        return 0.0, 0.0, center
    b0 = (t0 * s11 - t1 * s01) / det
    b1 = (t1 * s00 - t0 * s01) / det
    return b0, b1, center


def forecast_from_pool(pool, p1):
    """Quantile rows from the reference-class pool and the target's
    hour-1 print."""
    names = sorted(pool)
    log_ratios = {}
    log_h1 = {}
    for n in names:
        curve = pool[n]
        log_h1[n] = math.log(curve[1])
        log_ratios[n] = {h: math.log(curve[h] / curve[1])
                         for h in curve if h >= 2}
    b0, b1, center = fit_hour_slope(log_ratios, log_h1)
    target_log_h1 = math.log(max(1.0, p1))
    # Per-hour median and sd of the slope-adjusted log-ratios.
    medians = {}
    sds = {}
    for h in range(2, 25):
        bh = b0 + b1 * (h - 13) / 11.0
        vals = sorted(log_ratios[n][h] - bh * (log_h1[n] - center)
                      for n in names if h in log_ratios[n])
        if not vals:
            continue
        n = len(vals)
        mean = sum(vals) / n
        var = sum((x - mean) ** 2 for x in vals) / max(n - 1, 1)
        medians[h] = quantile(vals, 0.5)
        sds[h] = max(math.sqrt(var), SD_FLOOR)
    if not medians:
        raise ValueError("no usable hours in reference pool")
    rows = []
    for h in range(2, 25):
        if h in medians:
            med, sd = medians[h], sds[h]
        else:
            # No pool member has this hour: borrow the nearest hour's curve.
            near = min(medians, key=lambda k: (abs(k - h), k))
            med, sd = medians[near], sds[near]
        bh = b0 + b1 * (h - 13) / 11.0
        shift = bh * (target_log_h1 - center)
        q = []
        for z in Z:
            x = med + shift + z * sd
            x = max(-700.0, min(700.0, x))
            q.append(min(1e9, max(1.0, max(1.0, p1) * math.exp(x))))
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def persistence_forecast(p1):
    """Fallback: flat persistence with a widening normal spread."""
    p1 = max(1.0, p1)
    rows = []
    for h in range(2, 25):
        sd = BASE_SPREAD * math.sqrt(h - 1)
        q = [min(1e9, max(1.0, p1 * math.exp(z * sd))) for z in Z]
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def forecast_case(case):
    p1 = hour_one_print(case)
    try:
        pool = reference_pool(case)
    except (KeyError, ValueError, TypeError):
        pool = {}
    if len(pool) >= MIN_POOL_HARD:
        try:
            return forecast_from_pool(pool, p1)
        except (ValueError, ZeroDivisionError, OverflowError):
            pass  # any model failure falls through to persistence
    return persistence_forecast(p1)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        out = OUTPUT_DIR / f"{path.stem}.out"
        out.write_text(json.dumps(forecast, separators=(",", ":")) + "\n",
                       encoding="utf-8")


if __name__ == "__main__":
    main()
