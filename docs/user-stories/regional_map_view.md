---
name: Regional Map View
about: User story and acceptance criteria for the initial map view.
title: Regional map with zoom and pan
labels: Sprint 1
assignees: Anastasia Chepel

---

**As a** driver  
**I need** a map of Washington, Oregon, and Idaho that I can zoom and pan  
**So that** I can focus on the region where I'm traveling  

### Details and Assumptions
* Built with Leaflet and OpenStreetMap
* The map opens centered on the three-state region
* Panning and zooming out are limited to the region, so the user can't wander off to the rest of the world
* Each state has a visible border, the whole region has a darker outline, and the area outside it is dimmed
* Related requirements: FR-01, NFR-01

### Acceptance Criteria
```gherkin
Given the user opens the app
When the map loads
Then the map is centered on Washington, Oregon, and Idaho
And each state has a visible border and the area outside the region is dimmed
```

```gherkin
Given the map is displayed
When the user zooms in, zooms out, or drags the map
Then the map zooms and pans smoothly
And the map cannot be moved or zoomed out beyond the supported region
```
