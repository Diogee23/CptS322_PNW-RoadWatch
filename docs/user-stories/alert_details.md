---
name: Alert Details
about: User story and acceptance criteria for alert details.
title: View alert details by tapping a pin
labels: Sprint 1
assignees: Abby Gardner

---

**As a** driver  
**I need** to tap an alert pin and see its details  
**So that** I know what the alert is

### Details and Assumptions
* The popup shows the alert type, description, severity, location, last-updated time, and source agency (WA DOT, OR DOT, or ID DOT).
* Showing the source agency supports our requirement that alerts come from official DOT feeds.
* Related requirements: FR-10, NFR-07.

### Acceptance Criteria
```gherkin
Given alert pins are shown on the map
When the user taps a pin
Then a popup shows the alert's type, description, severity, location, last-updated time, and source agency
```
