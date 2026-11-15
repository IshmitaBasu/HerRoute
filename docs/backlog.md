# Implementation backlog

This local backlog replaces a remote issue board until a GitHub repository and account are available. Items are planned, not completed.

## Phase 2 — ingestion

- [x] Select pilot after inspecting source counts, spatial distribution and weak graph connectivity; investigate disconnected components in Phase 3.
- [x] Document source licenses, endpoints, observed fields, CRS, available timestamps and attribution; review provider terms again before publication.
- [x] Implement bounded lighting, OSM network and GTFS ingestion with manifests and source checks.
- [x] Run all three sources locally and document reproduction and failure cases; a fresh-checkout rerun remains to be independently verified.

## Phase 3 — spatial features

- [x] Validate geometries, project to EPSG:25833, retain graph identity and assess weak connectivity.
- [x] Compute length-weighted mapped-light proximity and nearest-stop distance with explicit unknown states.
- [x] Export matching graph and feature snapshot with checksums and a quality report.
- [x] Run a 10 m, 20 m and 30 m buffer sensitivity comparison; document the observed result and keep 20 m as the initial routing parameter.

## Phase 4 — AWS analytics

- [ ] After account and spending authorization, configure an AWS account/project boundary, IAM roles, S3, Glue Data Catalog, Athena workgroup scan limits and AWS Budgets.
- [ ] Build documented dbt-Athena staging and marts, validation tests and reproducible export.

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
