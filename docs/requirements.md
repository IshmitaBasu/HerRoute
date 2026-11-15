# Requirements and scope

Status: design, 14 November 2026. Implementation and evaluation remain future work.

## Problem and audience

People walking at night, including students, shift workers and commuters, may want to compare the distance of a walk with the presence of mapped public lighting and proximity to transit. Researchers may also want to inspect the method and its limitations. HerRoute will provide an explainable comparison, not advice or a prediction about personal safety.

## Core journey

1. Choose an origin and destination in the pilot area using map selections or other unambiguous controls.
2. The app checks the locations, snaps them to the walkable network and computes a shortest route.
3. Where a distinct, feasible alternative meeting the detour limit and improving the documented lighting proxy is found, show it alongside the baseline. Otherwise explain why it is unavailable; do not claim no such route exists unless the method establishes that.
4. Show both routes on a map and compare distance, estimated walking time, length-weighted mapped-light proximity and transit-stop proximity, including missing-data warnings.
5. Show source dates, attribution, parameters and limitations close to the results.

## Functional requirements

- Reject locations outside the pilot area, excessive snap distances, invalid or identical endpoints, and disconnected journeys with understandable messages.
- Calculate shortest paths using non-negative distance weights; retain edge identities in a multigraph.
- Apply a documented lighting-aware cost, a maximum 20% distance increase as an initial test parameter, and an explicit improvement check. Unknown lighting must not be treated as zero or as a known good value.
- Define coverage as the proportion of eligible route length within the specified distance of mapped lights; separately report the length with unknown data. Do not extrapolate known coverage across unknown segments.
- Estimate walking duration using a displayed, configurable constant speed; do not present it as a real-time prediction.
- Define transit proximity as distance to mapped stops, not service availability, accessibility or a guarantee of an operating connection. Document the exact route aggregation in implementation.
- Compute spatial features in batch; route requests read a coherent versioned graph and matching feature snapshot.
- Make source freshness, proxy assumptions and limitations visible. Avoid persistent journey history and personal profiles.

## Out of scope

Safety scores or guarantees, crime prediction, real-time lamp status or transit arrivals, user accounts, saved journeys, native apps and coverage beyond the pilot. Local MVP functionality must not depend on provisioned cloud resources.

## Acceptance and evaluation

- An unfamiliar tester can select valid endpoints, understand both results or the reason only one is shown, and locate limitations and attribution.
- Known graph cases verify shortest paths, detour and improvement constraints, unknown data and disconnected paths; GIS checks verify CRS and distance calculations.
- Rebuild instructions and source metadata permit reproduction; validation failure prevents promotion of a broken data snapshot.
- Evaluate 20–30 real pilot-area endpoint pairs and report failures, availability of alternatives, distance and coverage trade-offs, latency and sensitivity to parameters. Report actual measurements only.
- The final release also requires working CI, documented refresh, a public demo and an accessible evaluation as specified in the roadmap.
