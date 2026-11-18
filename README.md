# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zaidanainunn/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zaidanainunn/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts GTA VI's launch-day Twitch viewers hour by hour (hours 2–24, five quantiles each) from the hour-1 print and past launch curves. Model D: a size-conditioned median-ratio with an empirical spread — it fits the median log-ratio and spread only on comparable launches within one order of magnitude of the target's hour-1 print. Leave-one-game-out on 37 comparable launches: mean log pinball 0.6908 overall and 0.2110 on big launches, against the house baseline's 0.9297 / 0.2509.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `<id>.in` in the input directory and writes `<id>.out` to the output directory: 23 rows (hours 2–24), each with five quantiles (5/25/50/75/95%). Python 3.13, standard library only, no network, deterministic.

---

<sub>Entered on [make.fun](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)</sub>
