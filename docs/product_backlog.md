# Product Backlog: PNW RoadWatch
## Functional Requirements

| ID | Description | Priority | Sprint |
|---|---|---|---|
| FR-01 | Create a viewable map where the user can zoom in and out. | High | Sprint 1 |
| FR-02 | Integrate with Washington, Idaho, and Oregon DOT APIs to retrieve weather data and alerts. | High | Sprint 1 (started) |
| FR-03 | Normalize incoming state weather data and alerts into a common schema. | High | Sprint 1 (started) |
| FR-04 | Show weather data and alerts as pins on the map. | High | Backlog |
| FR-05 | Implement directions feature. | Medium | Backlog |
| FR-06 | Geo-tag alerts so that they can be filtered by route. | Medium | Backlog |
| FR-07 | Implement push notifications so users can see the live status of their route. | Low | Backlog |
| FR-08 | Implement route filters to avoid specific roads or conditions. | Low | Backlog |
| FR-09 | Allow users to save frequently used routes and locations for quick access. | Low | Backlog |
| FR-10 | Allow users to tap an alert pin to view its details (type, severity, location, last-updated time, source DOT agency). | High | Backlog |
| FR-11 | Display the most recent cached alert data, with a "last updated" timestamp, when the device has no internet connection. | Medium | Backlog |

## Non-Functional Requirements

| ID | Description | Priority | Sprint |
|---|---|---|---|
| NFR-01 | Render and function correctly on current Chrome, Safari, and Firefox, and on iOS and Android phones. | Medium | Sprint 1 (responsive layout) |
| NFR-02 | Alert data refreshes at least every 60 seconds while the app is open. | Medium | Backlog |
| NFR-03 | Support 1000 concurrent users with map load times under 3 seconds. | Low | Backlog |
| NFR-04 | Maintain 99% availability, measured monthly. | Low | Backlog |
| NFR-05 | At least 90% of users can identify alerts on their route within 30 seconds without instruction. | Medium | Backlog |
| NFR-06 | Map and alert data load within 3 seconds on a standard 5G connection. | Medium | Backlog |
| NFR-07 | Alert and route data sourced from official DOT feeds, with the source agency shown on each alert. | High | Backlog |
| NFR-08 | User location data and DOT API credentials encrypted in transit and never exposed to the client side. | High | Backlog |

## User Stories

| ID | Description | Related FRs | Priority | Sprint |
|---|---|---|---|---|
| US-01 | As a driver, I want to see live alerts as pins on a zoomable map, with severity shown by color or icon, so I understand where alerts are and how serious they are. | FR-01, FR-04, FR-10 | High | Sprint 1 (map portion) |
| US-02 | As a driver, I want directions between two points that show alerts along my route, so I can decide on an alternate path before driving. | FR-05, FR-06 | Medium | Backlog |
| US-03 | As a data administrator, I want WA, OR, and ID DOT data normalized into a common schema, so the app displays alerts reliably regardless of source format. | FR-02, FR-03 | High | Sprint 1 (started) |
| US-04 | As a driver, I want to filter out weather conditions, so I can avoid specific conditions on my route. | FR-08 | Low | Backlog |
| US-05 | As a commuter, I want a push notification when a new alert appears on my saved route, so I can adjust before I leave. | FR-07, FR-09 | Low | Backlog |

