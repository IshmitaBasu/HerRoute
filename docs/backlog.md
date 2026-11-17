# Implementation backlog

This local backlog tracks implementation status. Completed items have evidence in the repository or AWS console.

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

- [x] Configure the AWS project boundary, restricted IAM role, S3, Glue Data Catalog, Athena workgroup scan limit and AWS Budget alerts.
- [x] Build dbt-Athena staging and marts, validation tests, WKT export, and a reproducible source table definition.

## Phase 5 — routing

- [x] Implement and test baseline, feasible alternative, detour, improvement and failure handling.
- [x] Run route-weight sensitivity checks on two representative pilot-area journeys and retain penalty 2 as the initial documented default.

## Phase 6 — app

- [x] Build endpoint selection, map, comparison, source attribution and accessible limitations.
- [x] Test representative user flows, errors and missing data.

## Phase 7 — automation

- [x] Add CI, deterministic regression cases, controlled refresh and failure notifications.
- [x] Validate candidate snapshot promotion and preservation of the last valid warehouse source.

## Phase 8 — release

- [x] Add a reproducible, fixed 25-journey pilot evaluation set and offline result-summary command.
- [x] Evaluate 25 fixed pilot journeys and publish measured results, including unavailable alternatives and the graph-connectivity failure.
- [x] Deploy public demo after external accounts and publishing are authorized; live at `https://herroute-af9y.onrender.com` with server-side Places lookup.
- [x] Package the FastAPI application for a remote Docker build; add `/health` and server-side scoped Places API-key support.
- [x] Deploy the public demo on Render and confirm live address search and route comparisons.
- [ ] Capture final screenshots and a short demonstration.
- [ ] Update portfolio/CV only after release and authorization.
