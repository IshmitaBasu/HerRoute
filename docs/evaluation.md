# Pilot journey evaluation

This evaluation measures the routing engine on a fixed, reproducible set of 25 coordinate pairs inside the Alexanderplatz pilot boundary. Coordinates are used deliberately: the test measures routing outcomes without live address-search availability affecting the result.

## Design

`data/evaluation/pilot_journeys.csv` includes east-west, north-south and diagonal journeys across the pilot area. It is a structured pilot sample, not a statistically representative sample of all Berlin walking journeys. Each row is evaluated once using the approved local graph and segment-feature snapshot, with the documented default settings:

- lighting penalty: `2.0`
- maximum detour: `20%`
- transit-proximity penalty: `0.0`

An unavailable lighting-aware alternative is a valid route outcome, not an evaluation failure. A request is counted as an error only when the engine cannot produce a shortest route comparison.

## Run

From the repository root, after the local routing snapshot exists:

```powershell
python -m src.evaluation.run
```

The command writes two reproducible evidence files:

- `data/evaluation/results/journey_results.csv`: every journey, its baseline metrics, alternative metrics, difference metrics, runtime, and any valid unavailable-alternative reason.
- `data/evaluation/results/summary.json`: aggregate completion, alternative availability, distance, mapped-light-coverage and runtime distributions.

## Measures to report

Use the generated summary to report the following without describing mapped infrastructure as a safety measure:

- completed-request count and errors;
- proportion of journeys with a distinct, feasible lighting-aware alternative;
- distribution of additional walking distance and detour percentage;
- change in length-weighted mapped-light coverage in percentage points;
- route-computation runtime;
- reasons alternatives were unavailable.

## Results: 17 November 2026

The fixed 25-journey evaluation used lighting penalty `2.0`, maximum detour `20%`, and transit-proximity penalty `0.0`. The graph and feature snapshot were loaded once before timing each individual route comparison.

| Measure | Result |
| --- | ---: |
| Journeys requested | 25 |
| Completed route comparisons | 24 (96.0%) |
| Requests with a distinct, feasible lighting-aware alternative | 22 of 24 (91.67%) |
| Median additional distance where an alternative was returned | 66.35 m (2.97%) |
| Interquartile additional distance | 41.20-109.36 m (1.75-5.24%) |
| Maximum additional distance | 191.84 m (7.99%) |
| Median mapped-light coverage change | +6.08 percentage points |
| Interquartile mapped-light coverage change | +4.24 to +11.49 percentage points |
| Median route-computation time | 2,649.48 ms |
| Route-computation range | 2,447.01-2,893.61 ms |

Two completed requests correctly had no displayed alternative: one had no distinct lighting-aware candidate and one candidate would have exceeded the 20% detour limit. These are valid product outcomes, not errors.

One journey (`J09`, a diagonal route from `[13.409, 52.516]` to `[13.429, 52.529]`) could not be completed because no directed walking path connected its snapped graph nodes. This is retained as evidence of a graph-connectivity limitation in the pilot snapshot. It should not be interpreted as a statement about whether a person can walk between those physical locations.

The route runtimes are local measurements on the evaluation machine, exclude the one-time graph loading cost, and are not a hosted end-to-end latency benchmark. The improvements are differences in mapped-light coverage only. They do not measure illumination, lamp operation, transit service, crime, or personal safety.

The raw evidence is versioned with this repository at `data/evaluation/results/journey_results.csv` and `data/evaluation/results/summary.json`.
