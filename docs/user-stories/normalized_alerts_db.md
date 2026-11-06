---
name: Normalized Alerts
about: User story and acceptance criteria for normalizing WA, OR, and ID alert data into one common format.
title: Normalize alert data from all state APIs
labels: Sprint 2
assignees: Abby Gardner 
---

**As a** data admin  
**I need** incoming alert data to be normalized  
**So that** regardless of the API source, I can handle and manipulate the data and pass it on to the end user  

### Details and Assumptions
* Alerts come from three sources: WSDOT (Washington), ODOT TripCheck (Oregon), and Idaho 511
* A normalization layer (`normalize.py`) converts each agency's native format into one common alert schema
* The common schema has an ID, location, type, severity, description, last updated time, and source agency
* Each state has its own normalizer function, so a change to one agency's format only affects that function
* Severity uses four levels (low, moderate, high, critical), matching the map pins
* Records that are invalid or missing required fields are skipped instead of crashing the whole state's feed
* If one state's API fails, the other states still load
* Normalized alerts are stored in an `alerts` table (`db.py`) and served to the map through `GET /api/alerts`
* API keys are stored in `.env` and excluded from Git
* Related requirements: FR-02, FR-03, US-03

### Acceptance Criteria
```gherkin
Given the WA, OR, and ID DOT APIs are reachable
And each API returns valid alert data in its native format
When the normalization service runs its scheduled fetch
Then each state's data is converted into the common alert schema
And all normalized alerts are stored and available for map display
```

```gherkin
Given an alert has been normalized
When the alert is read from storage
Then it has an ID, location, type, severity, description, last updated time, and source agency
And its severity is one of low, moderate, high, or critical
```

```gherkin
Given an API returns a record that is invalid or missing required fields
When the normalization service processes the data
Then that record is skipped
And the remaining valid records from that state are still normalized and stored
```

```gherkin
Given one state's API is unavailable
When the normalization service runs its scheduled fetch
Then alerts from the other states are still normalized and stored
And the failure is recorded so it can be investigated
```
