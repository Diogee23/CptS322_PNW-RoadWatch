---
name: Route Finding (Directions)
about: User story and acceptance criteria for driving directions with route alerts.
title: Driving directions with alerts along the route
labels: Sprint 2
assignees: Anastasia Chepel

---

**As a** driver  
**I need** driving directions between two places, shown on the map with any alerts along the way  
**So that** I can choose a route and know about hazards before I leave  

### Details and Assumptions
* Start and destination are entered with Google Places autocomplete, and the route comes from the Google Routes API
* The route is drawn on the Leaflet map, and the map zooms to fit it
* The route summary shows total travel time and distance
* Alerts within 2 km of the route are listed above the step-by-step directions
* Clicking a step highlights it on the map and zooms to it
* Routes that leave Washington, Oregon, and Idaho show a warning, because the map only covers that region
* Related requirements: FR-05, FR-06, NFR-01

### Acceptance Criteria
```gherkin
Given the user is on the home page
When they pick a start location and a destination from the suggestions and click "Get Route"
Then the route is drawn on the map and the map zooms to fit it
And step-by-step directions are listed
```

```gherkin
Given a route is displayed
When there are active alerts within 2 km of the route
Then the number of alerts is shown with each alert's severity, type, and description
And when there are no alerts, a message says there are no active alerts along the route
```

```gherkin
Given step-by-step directions are displayed
When the user clicks a step
Then that step is highlighted in the list and on the map
And the map zooms to that part of the route
```

```gherkin
Given the user is on the home page
When the user requests a route
And part of the route is outside Washington, Oregon, and Idaho
Then a warning says that part of the route is outside the area the map covers
And the route is not displayed
```
