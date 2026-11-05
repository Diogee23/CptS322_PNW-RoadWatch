---
name: Live Alerts Backend
about: User story and acceptance criteria for the backend that retrieves and serves live road alerts.
title: Backend serves live WA, OR, and ID road alerts to the map
labels: Sprint 2
assignees: Hima Vasani

---

**As a** driver  
**I need** the map to show real, current road and weather alerts from the Washington, Oregon, and Idaho DOTs  
**So that** I can trust what I see on the map when I'm deciding whether and where to drive  

### Details and Assumptions
* The backend is a Flask app in `code/backend`. It calls WSDOT Highway Alerts, ODOT TripCheck Incidents, and Idaho 511 Winter Roads, and converts each one into our common alert format.
* The API endpoints and field names come from Abby's API scripts (PR #24).
* The alert format matches the `Alert` class from our class diagram (`alertID`, `location`, `alertType`, `severity`, `description`, `lastUpdated`, `sourceAgency`), so the map can read it with `Alert.fromJSON()` and no changes.
* Severity uses the same four levels as the map pins: low, moderate, high, critical. WA uses WSDOT's own priority, OR uses the incident type, and ID uses the road condition, plus keyword rules for closures, chains, ice, and snow.
* API keys are stored in a `.env` file on the server, never in the repo or sent to the browser. Abby and I set up the keys together.
* If no keys are set, the backend uses sample data so the team can still test and demo.
* If one state's API is down, the other states still load. If a state fails after working, its last good data is kept for up to 30 minutes. If nothing is available, the endpoint returns an error and the map shows its warning banner.
* Responses are cached for 60 seconds to match the map's refresh rate.
* Not included yet: hosting the backend publicly and switching the live site off mock data. That depends on picking a host.
* Related requirements: FR-02, FR-03, NFR-02, NFR-07, NFR-08, US-03.

### Acceptance Criteria
```gherkin
Given the WA, OR, and ID API keys are set up on the backend
When the frontend requests GET /api/alerts
Then the backend returns a list of current alerts from all three states
And each alert includes an ID, location, type, severity, description, last-updated time, and source agency
```

```gherkin
Given the backend returns alerts
When the map reads them with Alert.fromJSON()
Then every alert has valid coordinates and a severity of low, moderate, high, or critical
And each alert shows up as a pin without errors
```

```gherkin
Given one state's DOT API is down or returns an error
When the frontend requests GET /api/alerts
Then alerts from the other states are still returned
And GET /api/status shows which state failed and why
```

```gherkin
Given all of the DOT APIs are unavailable and no recent data is saved
When the frontend requests GET /api/alerts
Then the backend returns HTTP 503 with an error message
And the API keys do not appear in any response or error message
```

```gherkin
Given the backend test suite
When we run python -m pytest tests/backend
Then all tests pass
```
