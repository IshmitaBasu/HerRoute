# HerRoute: infrastructure-aware night-time walking routes

**Live demo:** [herroute-af9y.onrender.com](https://herroute-af9y.onrender.com)  
**Source code:** [github.com/IshmitaBasu/HerRoute](https://github.com/IshmitaBasu/HerRoute)

## The problem

Night-time walking decisions often involve more than distance. People may choose a longer route to stay closer to mapped public lighting or transit infrastructure. Those choices are especially familiar in conversations about women’s freedom of movement in cities.

HerRoute is a Berlin Alexanderplatz pilot that makes a limited set of infrastructure trade-offs visible. It compares a shortest walking route with a distinct alternative that can favour mapped-light coverage and proximity to mapped transit stops, within a stated detour limit.

It does not claim to identify a safe route. Mapped-light data cannot measure illumination, lamp condition, activity on a street, transit service, crime, or a person’s lived experience of safety.

## What I built

The project covers the data-engineering lifecycle from source ingestion to a public web application:

- collected a bounded OpenStreetMap walking network, mapped-light points, and transit-stop data for the pilot area;
- projected and validated spatial data in Python with GeoPandas, Shapely, OSMnx, and EPSG:25833;
- calculated length-weighted mapped-light coverage and nearest mapped-transit-stop distance for each walking segment;
- built an AWS analytics layer with S3, Glue, Athena, and dbt models and tests;
- implemented GitHub Actions CI, controlled candidate refresh and promotion workflows, and short-lived GitHub OIDC access to AWS;
- built a FastAPI interface with live AWS Location address autocomplete, an OpenStreetMap basemap, and transparent route-comparison metrics;
- packaged the app with Docker and deployed it to Render with no warehouse credentials in the public service.

The deployed application receives only a narrowly scoped Amazon Location API key for `Autocomplete` and `GetPlace`. It cannot access S3, Glue, Athena, dbt, or the private warehouse.

## Result

I evaluated a fixed set of 25 coordinate journeys across the pilot area using the documented default routing settings: lighting penalty `2.0`, maximum detour `20%`, and no transit-proximity penalty.

| Result | Measured outcome |
| --- | ---: |
| Completed route comparisons | 24 of 25 (96.0%) |
| Distinct, feasible lighting-aware alternatives | 22 of 24 (91.67%) |
| Median extra walking distance | 66.35 m (2.97%) |
| Median mapped-light coverage change | +6.08 percentage points |
| Median local route-computation time | 2.65 seconds |

Two valid comparisons did not produce an alternative: one had no distinct lighting-aware candidate, and one exceeded the 20% detour limit. One journey could not connect its snapped nodes in the directed walking graph. This is reported as a source-graph connectivity limitation, rather than being removed from the evaluation.

See the full [evaluation method and results](evaluation.md), including distributions and limitations.

## Architecture decisions

The interactive route engine intentionally uses a matching local graph and feature snapshot. The analytical warehouse has a separate controlled refresh and promotion path. This avoids silently changing user-facing routes when warehouse data changes.

The public demo uses a small versioned release snapshot in its Docker image. This keeps deployment inexpensive and reproducible, avoids exposing cloud data access, and fits a portfolio demonstration. Render’s free service can sleep when inactive, so it is not presented as a production availability guarantee.

## What I learned

This project reinforced that data products need explicit boundaries. Optimising a route around an infrastructure proxy can be useful when the metric is transparent, but it becomes harmful when it is presented as certainty about safety.

The technical work mattered: reproducibility, tests, access control, validation, spatial methodology, and deployment all made the result more trustworthy. The design decision that mattered most was also the simplest: clearly state what the data can and cannot say.

## Visual evidence

The final release will add:

1. a live route-comparison screenshot with the shortest and lighting-aware routes visible;
2. a GitHub Actions success screenshot showing the automated refresh or promotion workflow.
