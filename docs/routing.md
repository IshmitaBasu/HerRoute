# Routing methodology

## Route choices

HerRoute compares a conventional shortest walking route with a preference-aware candidate on the same validated directed OSM walking graph. The baseline minimizes segment length. The candidate normally minimizes a documented cost that increases when a segment has lower mapped-light coverage:

```text
lighting-aware cost = length_m × (1 + 2 × (1 - mapped_light_coverage_pct / 100))
```

The initial lighting penalty is 2. A segment with 0% known mapped-light coverage therefore costs three times its walking length in the candidate search; a fully covered segment keeps its physical length as cost. This is an explainable preference, not a claim that an alternative is safer.

If coverage is unknown, it stays unknown in the route metrics. The candidate search applies a fixed uncertainty cost rather than treating it as zero coverage.

The web interface also offers a **Near mapped transit** preference. It applies an optional additional multiplier:

```text
preference-aware cost = lighting-aware cost × (1 + transit_preference × min(nearest_mapped_stop_m / 200, 1))
```

The default transit preference is zero, so the default comparison remains lighting-aware. A higher setting favours segments closer to a mapped GTFS stop, capped at 200 m. It is a proximity proxy only: it does not measure walking access, service availability, accessibility, or night-time operation.

## Candidate acceptance

The candidate is displayed only when all of these conditions hold:

1. It is distinct from the shortest route.
2. Its walking distance is no more than 20% longer than the shortest route.
3. It has known mapped-light coverage.
4. Its length-weighted mapped-light coverage is higher than the shortest route's known coverage.

Otherwise, the product will show the shortest route and explain why no lighting-aware alternative is available.

## Route metrics

- **Distance:** sum of directed edge lengths in metres.
- **Estimated time:** distance divided by 75 metres per minute, an explicit walking-speed assumption.
- **Mapped-light coverage:** known covered length divided by known route length. Unknown length is reported separately and never treated as unlit.
- **Transit proximity:** length-weighted mean straight-line distance from route edges to their nearest mapped GTFS stop. It does not indicate walking access, service availability, accessibility, or night-time operation.

## First verified comparison

The initial local comparison used two fixed test coordinates within the pilot area on the 15 November 2026 snapshot. It produced a distinct lighting-aware candidate within the 20% detour limit.

| Metric | Shortest route | Lighting-aware candidate | Difference |
|---|---:|---:|---:|
| Distance | 1,667.9 m | 1,778.4 m | +110.5 m (+6.62%) |
| Estimated walking time | 22.24 min | 23.71 min | +1.47 min |
| Mapped-light coverage proxy | 79.27% | 94.08% | +14.81 percentage points |
| Mean nearest-stop distance | 41.32 m | 48.37 m | +7.05 m |
| Route length with unknown lighting coverage | 0 m | 0 m | — |

The candidate satisfies the engineering rule because its detour is below 20% and its known mapped-light coverage is higher. It does not establish that the candidate is safer, better illuminated in reality, or better served by transit.

For sensitivity checks, the local runner accepts a `--lighting-penalty` argument. Its `--summary` option prints only comparison metrics, leaving graph node and edge identifiers out of the terminal output.

## First route-weight sensitivity check

Using the same first verified journey, the route was evaluated with penalties of 0.5, 1, 2, and 3. A higher penalty places more importance on the mapped-light coverage proxy relative to walking distance.

| Lighting penalty | Candidate distance | Detour | Candidate coverage proxy | Result |
|---:|---:|---:|---:|---|
| 0.5 | 1,728.8 m | +3.65% | 90.73% | Distinct candidate accepted |
| 1 | 1,778.4 m | +6.62% | 94.08% | Distinct candidate accepted |
| 2 | 1,778.4 m | +6.62% | 94.08% | Same candidate as penalty 1 |
| 3 | 1,778.4 m | +6.62% | 94.08% | Same candidate as penalty 1 |

The lower penalty selected a shorter candidate with less mapped-light coverage. Penalty 1 was the first setting to select the higher-coverage route; higher values did not change this journey's result. This is evidence for one test journey only. Phase 5 will repeat the comparison across representative pilot-area journeys before selecting a default.

## Second verified comparison

A second cross-pilot journey at lighting penalty 1 also produced a feasible candidate.

| Metric | Shortest route | Lighting-aware candidate | Difference |
|---|---:|---:|---:|
| Distance | 2,564.9 m | 2,681.5 m | +116.7 m (+4.55%) |
| Estimated walking time | 34.20 min | 35.75 min | +1.56 min |
| Mapped-light coverage proxy | 91.58% | 97.57% | +5.99 percentage points |
| Mean nearest-stop distance | 99.93 m | 100.31 m | +0.37 m |
| Route length with unknown lighting coverage | 0 m | 0 m | — |

This candidate passes the 20% detour rule. Its modest transit-proximity difference should not be interpreted as a service-quality difference.

## Second route-weight sensitivity check

The second journey was also evaluated at each penalty setting.

| Lighting penalty | Candidate distance | Detour | Candidate coverage proxy | Result |
|---:|---:|---:|---:|---|
| 0.5 | 2,576.2 m | +0.44% | 93.24% | Distinct candidate accepted |
| 1 | 2,681.5 m | +4.55% | 97.57% | Distinct candidate accepted |
| 2 | 2,685.5 m | +4.70% | 97.71% | Distinct candidate accepted |
| 3 | 2,707.7 m | +5.57% | 98.07% | Distinct candidate accepted |

Penalty 2 remains the initial default. Compared with penalty 3, it gives nearly the same mapped-light coverage proxy on this journey while avoiding a further 22.2 m detour. This is a practical MVP choice, not a calibrated personal-safety setting.

## Verified rejection behavior

The second journey was rerun with a zero-detour limit. The engine returned the shortest route and correctly omitted the lighting-aware candidate because its distance was greater than the allowed limit. Together with the deterministic tests, this confirms that the product does not present an alternative that violates the configured detour constraint.

## Boundaries

`src.routing.run` is the local integration point: it accepts WGS84 longitude/latitude endpoints, rejects points outside the Alexanderplatz pilot boundary, snaps accepted points to walking-network nodes, and passes those nodes to the comparison engine. Snapping uses a local geographic distance approximation, avoiding OSMnx's optional `scikit-learn` dependency. Directed graph connectivity is retained: a path may be unavailable even when endpoints look close together on a map. The engine does not use crime data, personal history, or a safety score.
