# Sprint 1 Report 
Video Link: 
## What's New (User Facing)
 * Created a map of Oregon, Idaho and Washington
 * Added demo alerts to the map
 * Created a basic front-end site so that users can interact with the map
 * Added initial setup for directions feature 

## Work Summary (Developer Facing)
This sprint we had one person build the front-end website, one build the interactive map, another begin the backend, and our last team member begin the process of getting access to the Washington, Oregon, and Idaho DOT data feeds. We based the map's data model on our class diagram and developed it against sample alerts, so it can switch to the real API in the next sprint. We used GitHub issues, feature branches, and pull requests so that each part was reviewed before it was merged into main. Our biggest technical barrier was a mismatch between our planned tools and our hosting: we originally planned to build the map in React, but GitHub Pages can only serve static files, so we rewrote the map in plain JavaScript that loads Leaflet from a CDN. As a result, the published site currently shows sample alerts only, until the backend is hosted somewhere else. We also learned to be careful with credentials: a key committed to a public repository is visible to everyone, so we are restricting our site's API key and will keep the DOT API keys private. Obtaining DOT API access was also challenging because Oregon's documentation was poorly written and did not explain how to retrieve the API key. Finally, agreeing early on the alert data format and on where files live in the repository saved integration time, and we found that setting up shared tools like Node and Git takes longer than expected, so we plan for it earlier next sprint.

## Unfinished Work
- Map Feature (#6): The map itself is finished and merged, but it displays sample alerts instead of live DOT data. Connecting it depends on the backend alert endpoint, which was not ready this sprint. We checked off the acceptance criteria that are complete (region view, restricted map area) and left the live-data criteria unchecked. We commented on the issue to explain the dependency and moved it to Sprint 2.
- Normalization of data (#5): We started the backend but did not finish the services that fetch DOT data and convert it to our common alert schema. We commented that the work was larger than we anticipated and was slowed down by waiting on API access. Moved to Sprint 2.
- Connect DOT APIs (#1, #2, #12): We have obtained access to the Washington, Idaho, and Oregon DOT data. Oregon's documentation did not explain how to retrieve the API key, so this took longer than planned. We still need to build the backend connection that fetches the data, so these issues are moved to Sprint 2.
- Route finding, route filtering, and saved routes (#4, #20, #21): We did not start these because they depend on the map, backend, and DOT data working together, and we prioritized getting those foundations in place first. Moved to Sprint 2.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:
 * [URL of issue 1](https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/15)
 
 ## Incomplete Issues/User Stories
 Here are links to issues we worked on but did not complete in this sprint:
 * [URL of issue 1](https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/6) <The map feature is not yet complete because we need to add live alerts.>
 * [URL of issue 2](https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/12) <The Idaho API key is not yet connected because we still need to set up the backend.>
 * [URL of issue 3](https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/2) <The Oregon API key is not yet connected because we need to set up the backend.>
 * [URL of issue 4](https://github.com/Diogee23/CptS322_PNW-RoadWatch/issues/1) <The Washington API key is not yet connected because we need to set up the backend.>

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:
 * [roadwatch-map.js](https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/main/code/map/roadwatch-map.js)
 * [roadwatch-map.css](https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/main/code/map/roadwatch-map.css)
 * [main.js](https://github.com/Diogee23/CptS322_PNW-RoadWatch/blob/main/main.js)
 
## Retrospective Summary
Here's what went well:
  * Developing the initial map view
  * Developing the initial website
 
Here's what we'd like to improve:
   * Adding live alerts to the map
   * Improving the UI on the website
  
Here are changes we plan to implement in the next sprint:
   * Route finding
   * Real time alerts for Washington
   * Real time alerts for Oregon
   * Real time alerts for Idaho
   * Responsive layout for phone / desktop view
