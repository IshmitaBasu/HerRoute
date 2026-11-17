# HerRoute

HerRoute is a Berlin walking-route comparison app. It compares a shortest route with a preference-aware alternative that can favour proximity to mapped public lighting and mapped transit stops, when a meaningful alternative exists. Mapped lights are a proxy for infrastructure, not a measure or guarantee of safety or actual illumination.

Phases 1–7 are complete and Phase 8 release work is in progress. The public demo is live at [herroute-af9y.onrender.com](https://herroute-af9y.onrender.com). The project has a validated raw snapshot and processed walking-segment features for the Alexanderplatz pilot, plus a private S3, Glue, Athena, and dbt analytics layer. The browser interface uses AWS Location Places for live address suggestions, renders route alternatives on an OpenStreetMap basemap, and keeps favourites and feedback only in the user's browser. The route engine intentionally uses a matching graph and feature snapshot; warehouse promotion does not silently change interactive routes.

Every push and pull request to `main` runs the offline Python test suite without cloud credentials or live data downloads. Candidate refresh and Athena/dbt promotion are separate reviewed GitHub Actions workflows that use short-lived GitHub OIDC roles.

## Run locally

The local app requires Python 3.11, the AWS CLI v2, and an AWS identity with `geo-places:Autocomplete` and `geo-places:GetPlace` permission in `eu-central-1`. Never commit AWS credentials or a personal AWS profile to this repository.

On Windows PowerShell, create the environment and install the application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Raw and processed data artifacts are intentionally not stored in Git. Build the local Berlin pilot snapshot before starting the app:

```powershell
python -m src.ingestion.download
python -m src.geospatial.process
```

Sign in to AWS, then start the local web server:

```powershell
aws login --region eu-central-1
python -m uvicorn src.web.app:app --reload
```

Open `http://127.0.0.1:8000` in a browser. Keep the server terminal open while using the application. Address suggestions are live AWS Location requests; the map uses live OpenStreetMap tiles; route calculations use the local, validated pilot snapshot. Run `python -m pytest -q` to validate the test suite.

Downloads require internet access and may be large. Data and the OSMnx request cache are ignored by Git; OSMnx may reuse cached responses on subsequent runs. A manifest appears only after every source validates; a failed run can leave partial raw files, which must not be treated as a validated snapshot.

## Public-demo deployment design

The public demo is packaged as a Docker image that contains only the approved `walk.graphml` and `segment_features.parquet` routing artifacts. Those two files are copied into the small, versioned `data/release/` deployment snapshot so GitHub and Render can build the image without AWS data access. A health endpoint is available at `/health`. Render's free web-service tier builds the image remotely, so a local Docker installation and its disk use are unnecessary. It may sleep after idle time; this is acceptable for a portfolio demo but not a production availability guarantee.

The hosted server receives `HERROUTE_LOCATION_API_KEY` as an encrypted host secret. This is a narrowly scoped Amazon Location API key that permits only `geo-places:Autocomplete` and `geo-places:GetPlace` against the default Places provider. It remains on the server and is never sent to browsers, committed to Git, or substituted for AWS account credentials. Local development continues to use the developer's authenticated AWS identity. The public app does not receive S3, Glue, Athena, dbt, or warehouse credentials.

The deployed demo was verified with fresh Amazon Location address selections and a completed route comparison. It is a portfolio demonstration, so the free Render service can sleep after inactivity and the first request after that may take longer.

## Pilot evaluation

On 17 November 2026, a fixed 25-journey Alexanderplatz evaluation completed 24 route comparisons. Twenty-two of those 24 comparisons (91.67%) returned a distinct, feasible lighting-aware alternative. Across those alternatives, the median extra distance was 66.35 m (2.97%), while median mapped-light coverage increased by 6.08 percentage points. One journey could not be routed because its snapped graph nodes had no directed walking path; this is retained as a graph-connectivity limitation. Full method, results and limits are in the [pilot evaluation](docs/evaluation.md).

- [Requirements and success criteria](docs/requirements.md)
- [Architecture and data contracts](docs/architecture.md)
- [Assumptions and pilot-area decision](docs/assumptions.md)
- [Source discovery and coverage gate](docs/data_sources.md)
- [Feature methodology and quality report](docs/methodology.md)
- [AWS analytics setup and warehouse models](docs/aws_analytics.md)
- [Routing methodology](docs/routing.md)
- [Interactive application and privacy boundaries](docs/web_interface.md)
- [Pilot journey evaluation design](docs/evaluation.md)
- [Portfolio case study](docs/portfolio_case_study.md)
- [UI wireframe](docs/wireframe.md)
- [Implementation backlog](docs/backlog.md)
- [Original roadmap](Project%20Roadmap.md)
