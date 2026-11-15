# Implementation backlog

This local backlog replaces a remote issue board until a GitHub repository and account are available. Items are planned, not completed.

## Phase 2 — ingestion

- [ ] Validate candidate pilot and compare another area if needed; record counts, spatial distribution and final bounds.
- [ ] Verify source licenses, endpoints, field definitions, CRS and versions; document attribution and fetch policies.
- [ ] Implement repeatable, bounded lighting, OSM network and GTFS ingestion with manifests and source checks.
- [ ] Demonstrate a clean download and document reproduction and failure cases.

## Phase 3 — spatial features

- [ ] Validate geometries, project to metric CRS, retain graph identity and assess connectivity.
- [ ] Compute length-weighted light proximity and stop distance with explicit unknown states.
- [ ] Export matching graph and feature snapshot and quality report.

## Phase 4 — warehouse

- [ ] After account and spending authorization, configure BigQuery and budget controls.
- [ ] Build documented dbt staging and marts, validation tests and reproducible export.

## Phase 5 — routing

- [ ] Implement and test baseline, feasible alternative, detour, improvement and failure handling.
- [ ] Run sensitivity analysis for distance buffer and route weights.

## Phase 6 — app

- [ ] Build endpoint selection, map, comparison, source attribution and accessible limitations.
- [ ] Test representative user flows, errors and missing data.

## Phase 7 — automation

- [ ] Add CI, deterministic regression cases, controlled refresh and failure notifications.
- [ ] Validate clean setup, snapshot promotion and preservation of last valid data.

## Phase 8 — release

- [ ] Evaluate 20–30 journeys and publish measured results and limitations.
- [ ] Deploy public demo after external accounts and publishing are authorized; create README, screenshots, demo and case study.
- [ ] Update portfolio/CV only after release and authorization.
