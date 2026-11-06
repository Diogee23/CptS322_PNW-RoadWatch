---
name: UI Styling and Polish
about: User story and acceptance criteria for a polished, consistently styled website.
title: Attractive, polished website styling
labels: Sprint 2
assignees: Emily Tran
---

**As an** end user  
**I need** an attractive, polished-looking website  
**So that** the app feels pleasant to use  

### Details and Assumptions
* The app uses a defined color palette (a primary color, an accent color, and a neutral background) applied consistently across the page
* One or two fonts are used, with a clear size hierarchy for headings, body text, and small labels
* A header or navigation bar shows the PNW RoadWatch name and a logo or icon
* The route inputs, buttons, and directions panel are styled as cards or panels with padding instead of raw browser defaults
* Buttons and form fields share one consistent style, including hover and focus states
* Spacing and alignment are consistent between the map, the inputs, and the directions panel
* The Leaflet map keeps its current functionality, and its surroundings (border, container, controls) are styled to match the rest of the page
* Styling uses plain CSS and does not change how any feature works
* Related requirements: NFR-01, NFR-05

### Acceptance Criteria
```gherkin
Given the user opens the website
When the page loads
Then a styled header shows the PNW RoadWatch name
And the colors and fonts match the chosen palette and are consistent across the page
```

```gherkin
Given the user is on the home page
When they view the route inputs, buttons, map, and directions panel
Then the inputs, directions and map appear inside styled panels with padding
And spacing and alignment between the map, inputs, and directions panel are consistent
```

```gherkin
Given the team compares the page before and after this issue
When the changes are reviewed
Then the site looks noticeably more polished
And all existing features (route finding, alerts, map interaction) still work as before
```
