---
name: Alert Pins With Severity
about: User story and acceptance criteria for alert pins.
title: Show alerts as pins with colors based on severity
labels: Sprint 1
assignees: Hima Vasani

---

**As a** driver  
**I need** alerts shown as pins on the map, with severity clearly marked  
**So that** I can see where problems are and how serious they are

### Details and Assumptions
* Each alert has a location (latitude and longitude) and a severity: low, moderate, high, or critical.
* Pins have different colors and symbols to indicate levels of severity.
* Currently runs on demo alerts until the backend alert endpoint is available.
* Related requirements: FR-04, US-01.

### Acceptance Criteria
```gherkin
Given alert data is available
When the map loads
Then each alert appears as a pin at its correct location
And the pin's color and symbol show its severity
```
