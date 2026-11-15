# Assumptions, safeguards and pilot

## Provisional pilot

Use a small rectangular area around Alexanderplatz, central Berlin, as the **candidate**, bounded by WGS84 longitude 13.395–13.430 and latitude 52.515–52.530. This is an operational bounding box, not an administrative boundary. It is a manageable urban area with transit access; it is not a claim that its data are complete or representative of all Berlin.

The source catalogs describe Berlin-wide public-lighting data and VBB transit data, but no street-level extraction or quantitative coverage comparison has been performed. The pilot is therefore **not yet validated or final**. In Phase 2, retrieve all three sources inside the box plus a documented processing buffer, inspect counts, spatial distribution, connectivity and source metadata, and compare at least one alternative candidate if the data are sparse or disconnected. Record the evidence and final bounds before using the area for evaluation. A missing light is not proof that a street is unlit.

## Initial modelling choices

- Use 20 m from a mapped light as a sensitivity-tested geometric proxy, not an illumination radius; test at least two other radii and document results.
- Test a maximum 20% extra distance against the shortest route. A candidate must be connected, distinct, within the limit and show a measurable proxy improvement; the method may fail to find an existing feasible alternative.
- Use a configurable walking speed, initially 4.5 km/h, without accounting for individual mobility, crossings, elevation or delays.
- A source fetch failure, unknown coverage or incomplete source extent is distinct from a valid observation of zero nearby lights. Where completeness cannot be established, mark the affected coverage unknown and avoid claiming an improvement based on it.
- Proximity to a stop is straight-line distance unless explicitly stated otherwise; it does not represent walking access, schedules or service at night.
- A finite processing buffer can affect routes near the boundary. Check connectivity and boundary effects and disclose them; do not route outside the validated graph.

## Ethical and privacy safeguards

Never label a route safe or safer, infer crime or personal risk, or imply a mapped lamp is on, functional or provides sufficient light. Display freshness and uncertainty near comparisons. Do not create profiles or retain journey histories; avoid request coordinates in logs and analytics. Respect source licenses and service limits. Budget alerts are not spending caps; cloud setup requires an explicitly authorized account and budget.
