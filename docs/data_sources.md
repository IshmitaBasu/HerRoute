# Source discovery and Phase 2 coverage gate

Reviewed 14 November 2026. This is catalog research, not a downloaded dataset or a validation of local completeness.

| Source | Catalog evidence | Work remaining |
|---|---|---|
| [Berlin public lighting WFS](https://daten.berlin.de/datensaetze/offentliche-beleuchtung-wfs-77fc5415) | Public-light positions; catalog describes Berlin coverage and Datenlizenz Deutschland Zero 2.0. [Provider metadata](https://gdi.berlin.de/geonetwork/geonetwork/api/records/495d3fc0-13b4-362a-b79a-f1b32683e282) describes quarterly maintenance. | Inspect actual endpoint, schema, CRS, paging, availability, source date and pilot distribution; establish what can be known about completeness. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | OSM is the planned walking-network source. Its data require attribution and are subject to ODbL. | Verify extraction limits, walkability filters, network connectivity, data date and applicable attribution/share-alike obligations for produced artifacts. |
| [VBB static GTFS](https://unternehmen.vbb.de/digitale-services/datensaetze/) | Provider publishes static transit datasets; [Berlin catalog](https://daten.berlin.de/datensaetze/vbb-fahrplandaten-via-gtfs) specifies VBB attribution. | Check the exact downloaded feed's license and terms, stop fields, timestamps and distribution. Record the stated attribution. |

Provider pages may disagree on refresh frequency or lag behind the data; record the actual feed metadata and retrieval time and verify terms when implementing. Phase 2 must save counts and bounds, examine the distribution of lights and stops, assess network connectivity and compare candidates if needed. Do not interpret counts or provider-wide geographic scope as proof of comprehensive mapping. Log source failures separately from empty but valid results.

## Discovery on 15 November 2026

The WFS capabilities identify `beleuchtung:beleuchtung`, default CRS EPSG:25833 and GeoJSON output. A WFS 1.0 EPSG:4326 query returned 4,970 features; 4,759 fall within the buffered bounds (13.390–13.435 E, 52.512–52.533 N). The service also returned points just outside the requested box, which are filtered locally. Observed geometries are MultiPoint; source properties include IDs, street and lamp type. The [VBB provider page](https://unternehmen.vbb.de/digitale-services/datensaetze/) identifies the static GTFS feed as CC BY 4.0; attribute “VBB Verkehrsverbund Berlin-Brandenburg GmbH” and link the license.

Inside the unbuffered pilot were 2,877 light features and 668 GTFS stop records; every cell of a 3×3 grid contained both. Stop records may include platforms and station entries rather than distinct stations. The buffered walk graph had 7,860 nodes, 19,516 directed edges and 113 weak components; its largest component contained 7,591 nodes. Of 4,414 nodes in the unbuffered pilot, 4,259 were in that largest component. These checks support proceeding with the selected pilot but do not demonstrate complete data, actual lighting, directed reachability or safe walking routes. Phase 3 must investigate the disconnected parts and boundary effects.

The script downloads the whole GTFS archive temporarily because stops are provided inside the feed, then extracts only stops within the buffered area. It records archive and artifact checksums and available HTTP metadata. Missing stop coordinates are skipped; their location and relevance cannot be inferred. Source timestamps may be unavailable and are not replaced with retrieval timestamps. OSM data are obtained via OSMnx's public Overpass service and may change between runs; output checksums describe a retrieved snapshot, not a fixed historical OSM version. Refresh must respect provider service limits.
