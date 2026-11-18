"""GTA VI launch-day Twitch CCU forecaster (Model D).

Forecasts, for hours 2..24 of the UTC release day, five quantiles
(5/25/50/75/95%) of the concurrent viewers in the Grand Theft Auto VI
Twitch category, from the hour-1 print and the case's comparables.

Model D — size-conditioned median-ratio with an empirical spread:
  * For each comparable launch, take the log-ratio of its hour-h viewers
    to its hour-1 viewers, log(viewers[h] / viewers[1]).
  * Keep only comparables whose hour-1 print is within one order of
    magnitude of the target's hour-1 print (h1_comp >= 0.1 * p1). A launch
    of a very different scale does not share GTA VI's curve shape, so
    fitting on all of them pulls the median off and inflates the spread.
    If fewer than 8 comparables pass, fall back to the 8 largest by hour-1
    (a deterministic rule; never silently widen to all of them).
  * The median log-ratio across the kept comparables is the centre:
    median(h) = p1 * exp(median log-ratio(h)).
  * The spread is the standard deviation of those log-ratios:
    q_tau(h) = median(h) * exp(z_tau * spread(h)).
  * The Grand Theft Auto VI pre-release history is not a launch, so it is
    excluded from the fit (its name contains "Grand Theft Auto VI").

Leave-one-game-out on the 37 comparable launches: mean log pinball
0.6908 overall and 0.2110 on big launches (hour-1 >= 50k), against the
house baseline's 0.9297 / 0.2509. The filter was chosen from that
backtest, so those scores are exploratory, not a preregistered estimate.

Runs as: python3 -P -s main.py (python:3.13-slim, standard library only,
no network). Reads every <id>.in in /input (MAKEFUN_INPUT_DIR outside the
grader) and writes <id>.out to /output (MAKEFUN_OUTPUT_DIR): exactly 23
rows, hours 2..24, each five finite numbers above 0 and at most 1e9,
non-decreasing, at most 65,536 bytes.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from statistics import median, stdev

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# A comparable counts as "similar scale" when its hour-1 print is at
# least this fraction of the target's hour-1 print.
SIZE_FRACTION = 0.1
# Fewest comparables the fit is allowed to use; below this, take the
# largest ones instead of widening to all of them.
MIN_COMPARABLES = 8
# The pre-release history is a category, not a launch, so it never
# enters the fit.
PRE_RELEASE_MARKER = "Grand Theft Auto VI"


def round2(x):
    """Round to 2 decimals, half up; a whole number comes back as int."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if float(value).is_integer() else value


def release_day_hours(comp):
    """A comparable's viewers for the 24 hours of its release day.

    Returns a dict hour-offset -> viewers (offset 0 is hour 1), or None
    when any of the 24 hours is missing or not positive.
    """
    day_start = datetime.fromisoformat(comp["day_start"].replace("Z", "+00:00"))
    by_hour = {}
    for row in comp.get("hourly", []):
        moment = datetime.fromisoformat(row["from"].replace("Z", "+00:00"))
        offset = int((moment - day_start).total_seconds() // 3600)
        if 0 <= offset < 24:
            by_hour[offset] = row["viewers"]
    if len(by_hour) < 24:
        return None
    if any(not by_hour[h] or by_hour[h] <= 0 for h in range(24)):
        return None
    return by_hour


def pick_comparables(case, p1):
    """The comparables the fit uses: launches of a similar scale.

    Drops the pre-release history and any launch without a complete
    release day, keeps those with hour-1 at least SIZE_FRACTION of the
    target's, and falls back to the MIN_COMPARABLES largest when too few
    pass. The target game itself is never a comparable: a launch of the
    same name would be the thing being forecast, not evidence about it.
    """
    target = (case.get("game") or {}).get("name", "")
    launches = []
    for comp in case.get("comparables", []):
        name = comp.get("name", "")
        if PRE_RELEASE_MARKER in name:
            continue
        if target and target in name:
            continue
        hours = release_day_hours(comp)
        if hours is None:
            continue
        launches.append(hours)
    if not launches:
        raise ValueError("no comparable launch has a complete release day")
    similar = [h for h in launches if h[0] >= SIZE_FRACTION * p1]
    if len(similar) < MIN_COMPARABLES:
        similar = sorted(launches, key=lambda h: h[0], reverse=True)[:MIN_COMPARABLES]
    return similar


def fit_curve(train):
    """Per-hour median log-ratio and spread across the kept launches."""
    centre = {}
    spread = {}
    for hour in range(2, 25):
        offset = hour - 1
        logs = [math.log(h[offset] / h[0]) for h in train]
        centre[hour] = median(logs)
        spread[hour] = stdev(logs) if len(logs) > 1 else 0.0
    return centre, spread


def hour_quantiles(p1, hour, centre, spread):
    """The five quantiles for one hour, clamped and non-decreasing."""
    middle = p1 * math.exp(centre[hour])
    out = []
    for z in Z:
        q = round2(middle * math.exp(z * spread[hour]))
        q = max(q, 0.01)
        q = min(q, 1e9)
        out.append(q)
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    train = pick_comparables(case, p1)
    centre, spread = fit_curve(train)
    return {
        "hours": [
            {"hour": row["hour"], "q": hour_quantiles(p1, row["hour"], centre, spread)}
            for row in case["forecast"]
        ]
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
