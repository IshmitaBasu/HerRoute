# HerRoute

HerRoute is a planned Berlin walking-route comparison app. It will compare a shortest route with a route that favors proximity to mapped public lighting, when a meaningful alternative exists. Mapped lights are a proxy for infrastructure, not a measure or guarantee of safety or actual illumination.

The project has completed **Phase 5: routing**. It has a validated raw snapshot and processed walking-segment features for the Alexanderplatz pilot, plus a private S3, Glue, Athena, and dbt analytics layer. The tested route-comparison engine validates pilot endpoints, produces a shortest route and a constrained lighting-aware candidate, and documents its limitations. The interactive app remains planned.

To set up on Windows with Python 3.11: `python -m venv .venv`, then `.venv\Scripts\python -m pip install -r requirements.txt`. Run `.venv\Scripts\python -m src.ingestion.download` to retrieve the buffered pilot data, and `.venv\Scripts\python -m pytest -q` for offline tests. Downloads require internet access and may be large. Data and the OSMnx request cache are ignored by Git; OSMnx may reuse cached responses on subsequent runs. A manifest appears only after every source validates; a failed run can leave partial raw files, which must not be treated as a validated snapshot.

- [Requirements and success criteria](docs/requirements.md)
- [Architecture and data contracts](docs/architecture.md)
- [Assumptions and pilot-area decision](docs/assumptions.md)
- [Source discovery and coverage gate](docs/data_sources.md)
- [Feature methodology and quality report](docs/methodology.md)
- [AWS analytics setup and warehouse models](docs/aws_analytics.md)
- [Routing methodology](docs/routing.md)
- [UI wireframe](docs/wireframe.md)
- [Implementation backlog](docs/backlog.md)
- [Original roadmap](Project%20Roadmap.md)
