# HerRoute

HerRoute is a Berlin walking-route comparison app. It compares a shortest route with a preference-aware alternative that can favour proximity to mapped public lighting and mapped transit stops, when a meaningful alternative exists. Mapped lights are a proxy for infrastructure, not a measure or guarantee of safety or actual illumination.

The project has completed **Phase 6: interactive application**. It has a validated raw snapshot and processed walking-segment features for the Alexanderplatz pilot, plus a private S3, Glue, Athena, and dbt analytics layer. The browser interface uses AWS Location Places for live address suggestions, renders route alternatives on an OpenStreetMap basemap, and keeps favourites and feedback only in the user's browser. The route engine still uses the matching local graph and feature snapshot; cloud-hosted route serving and scheduled refresh are future work.

Phase 7 has begun with GitHub Actions CI. Every push and pull request to `main` runs the offline Python test suite without cloud credentials or live data downloads.

## Run locally

The local app requires Python 3.11, the AWS CLI v2, and an AWS identity with `geo-places:Autocomplete` and `geo-places:GetPlace` permission in `eu-central-1`. Never commit AWS credentials or a personal AWS profile to this repository.

On Windows PowerShell, create the environment and install the application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The large routing artifacts are intentionally not stored in Git. Build the local Berlin pilot snapshot before starting the app:

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

- [Requirements and success criteria](docs/requirements.md)
- [Architecture and data contracts](docs/architecture.md)
- [Assumptions and pilot-area decision](docs/assumptions.md)
- [Source discovery and coverage gate](docs/data_sources.md)
- [Feature methodology and quality report](docs/methodology.md)
- [AWS analytics setup and warehouse models](docs/aws_analytics.md)
- [Routing methodology](docs/routing.md)
- [Interactive application and privacy boundaries](docs/web_interface.md)
- [UI wireframe](docs/wireframe.md)
- [Implementation backlog](docs/backlog.md)
- [Original roadmap](Project%20Roadmap.md)
