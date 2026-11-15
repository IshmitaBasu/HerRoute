# MVP wireframe

Design only; no UI has been implemented.

```text
HerRoute — walking infrastructure comparison
Mapped lights do not guarantee illumination or safety.

Origin      [ Select on map / search within pilot ]
Destination [ Select on map / search within pilot ]
[ Compare routes ]

+--------------------------+----------------------------------+
| Route comparison         | Map                              |
| Shortest                 | Start/end markers                |
| distance, estimated time | Shortest route: solid line       |
| mapped-light proximity   | Alternative: contrasting line    |
| unknown data length      | Legend and attribution           |
| nearest transit summary  |                                  |
|                          |                                  |
| Alternative, if found    |                                  |
| same metrics + detour    |                                  |
| otherwise: explanation   |                                  |
+--------------------------+----------------------------------+
Source dates • Method and assumptions • Data limitations
```

Controls must be usable without relying on color alone. Results should explicitly explain incomplete coverage, uncertain lighting, the walking-speed assumption and the absence of live transit information. Input errors and no-route results appear in text. The final map/input library and accessibility review remain implementation tasks.
