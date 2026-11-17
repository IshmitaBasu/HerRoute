# Interactive web interface

HerRoute's interface is a FastAPI application for the Alexanderplatz pilot. It runs locally during development and is packaged for a low-cost public demonstration while retaining the routing engine's documented limits.

## Endpoint selection and routing

- Address suggestions appear after three characters through AWS Location Places. Requests are restricted to Germany and the pilot bounding box.
- Selecting an address retrieves its coordinate only for the current route request. AWS Places results use the `SingleUse` setting.
- The web API loads the matching local `walk.graphml` and `segment_features.parquet` snapshot, calculates the shortest route and an optional preference-aware alternative, and returns browser-safe route geometry and metrics.
- Leaflet displays the two route geometries over OpenStreetMap tiles. Map display and address lookup are live services; routing uses the approved graph and feature snapshot bundled with the application. Warehouse refresh/promotion is intentionally separate from this interactive snapshot.

## Hosted-demo boundaries

The Docker image contains only `walk.graphml` and `segment_features.parquet`, sourced from the versioned `data/release/` deployment snapshot, and `/health` provides a credential-free liveness response for the hosting platform. The selected Render free tier builds remotely and may sleep after idle time. Its encrypted `HERROUTE_LOCATION_API_KEY` secret is used server-side for the two Places actions required by the interface: `Autocomplete` and `GetPlace`. It is not exposed to browser JavaScript. The public demo receives no AWS account credentials and cannot read or modify S3, Glue, Athena, or dbt resources.

## Preferences and explanation

The interface provides presets for balanced walking, brighter streets, shorter walking, and nearer mapped transit. The controls set the documented lighting penalty, optional mapped-transit proximity penalty, and maximum detour. When a comparison is submitted, the action changes to a visible **Finding your route** loading state until the request completes. The **Why this route?** panel reports the resulting distance, mapped-light-coverage, and mapped-stop-proximity trade-offs. These signals are infrastructure proxies and must not be interpreted as a personal-safety score, illumination measurement, or service guarantee.

Users can select a light or dark theme. HerRoute defaults to the browser's colour-scheme preference until the user makes a choice, then remembers that choice only in the browser.

## Local-only personal controls

Saved places have a user-provided label, such as Home or Work, and can be applied directly as a new From or To address. Users can remove them at any time. Saved places, theme preference, and private route notes are stored in the browser's `localStorage`. They are not sent to HerRoute, AWS, or the analytics warehouse.

Private route notes are deliberately not presented as submitted feedback because the application has no feedback-collection service. Users can download their own notes as JSON or clear them from their browser. A copied route link contains the selected address identifiers and labels so another person can reproduce that comparison; it does not include saved places, theme preference, or private notes. Users should treat that link as location-sensitive and share it deliberately.

## Time context

The interface displays the browser's local time to provide night-walking context. It explicitly states that live lighting condition, disruption, and transit-service data are not included.
