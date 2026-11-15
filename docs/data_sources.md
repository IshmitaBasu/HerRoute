# Source discovery and Phase 2 coverage gate

Reviewed 14 November 2026. This is catalog research, not a downloaded dataset or a validation of local completeness.

| Source | Catalog evidence | Work remaining |
|---|---|---|
| [Berlin public lighting WFS](https://daten.berlin.de/datensaetze/offentliche-beleuchtung-wfs-77fc5415) | Public-light positions; catalog describes Berlin coverage and Datenlizenz Deutschland Zero 2.0. [Provider metadata](https://gdi.berlin.de/geonetwork/geonetwork/api/records/495d3fc0-13b4-362a-b79a-f1b32683e282) describes quarterly maintenance. | Inspect actual endpoint, schema, CRS, paging, availability, source date and pilot distribution; establish what can be known about completeness. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | OSM is the planned walking-network source. Its data require attribution and are subject to ODbL. | Verify extraction limits, walkability filters, network connectivity, data date and applicable attribution/share-alike obligations for produced artifacts. |
| [VBB static GTFS](https://unternehmen.vbb.de/digitale-services/datensaetze/) | Provider publishes static transit datasets; [Berlin catalog](https://daten.berlin.de/datensaetze/vbb-fahrplandaten-via-gtfs) specifies VBB attribution. | Check the exact downloaded feed's license and terms, stop fields, timestamps and distribution. Record the stated attribution. |

Provider pages may disagree on refresh frequency or lag behind the data; record the actual feed metadata and retrieval time and verify terms when implementing. Phase 2 must save counts and bounds, examine the distribution of lights and stops, assess network connectivity and compare candidates if needed. Do not interpret counts or provider-wide geographic scope as proof of comprehensive mapping. Log source failures separately from empty but valid results.
