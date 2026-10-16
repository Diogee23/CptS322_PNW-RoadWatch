---
name: Basic User Interface
about: User story and acceptance criteria for the basic user interface.
title: Basic web interface for PNW RoadWatch
labels: Sprint 1
assignees: Emily Tran

---

**As a** driver  
**I need** a simple web page with the map and a place to enter my start and destination  
**So that** I can use PNW RoadWatch from my browser without installing anything  

### Details and Assumptions
* Built with HTML, CSS, and JavaScript, and published on GitHub Pages.
* The page has a header with the app name and a short description, a map area, and a "Get Directions" section.
* The "Get Directions" form has a starting location field and a destination field, both with place suggestions as the user types (Google Maps autocomplete).
* The map is added to the page's map area.
* Not included yet: sending the entered locations to get a route (the "Get Route" button does nothing yet), and a warning when a location is outside Washington, Oregon, or Idaho. These are planned for a later sprint.
* Related requirements: NFR-01, FR-05 (partly).

### Acceptance Criteria
```gherkin
Given alert data is available
And the user opens the site in Chrome, Safari, or Firefox
When the page loads
Then the user sees the PNW RoadWatch header, the map area, and the "Get Directions" form
```

```gherkin
Given the "Get Directions" form is displayed
When the user types in the starting location or destination field
Then matching place suggestions appear
And the user can select one to fill in the field
```
