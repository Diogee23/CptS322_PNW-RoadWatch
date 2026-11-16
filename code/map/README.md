# Map Feature (MapView)
Interactive map for PNW RoadWatch. It shows DOT alerts as pins on a zoomable map limited to Washington, Oregon and Idaho. Built with React, Leaflet and OpenStreetMap.

## What it does
- Zoomable, pannable map locked to the WA / OR / ID region
- State borders, an outline around the whole region, and dimming outside it
- Alert pins with different colors based on severity (low, moderate, high, critical), each with a symbol
- Tap a pin to see type, description, severity, location, last-updated time and source agency
- Refreshes alerts every 60 seconds
- "My location" button: shows a blue dot with an accuracy circle, follows the user as they move, and centers the map on them (needs HTTPS or `localhost`, and the user must allow location access)

## Files
| File | Purpose |
|---|---|
| `roadwatch-map.js` | The map: `Location`, `Alert`, `AlertDatabase` and `MapView` classes, alert refresh, offline cache, location button |
| `roadwatch-map.css` | Pin, banner, popup and location button styles |
| `roadwatch-directions.js` | `DirectionsController`: route drawing, step-by-step directions, alerts along the route |
| `directions.css` | Styles for the directions panel |
| `us-states.json` | State boundary data used for the borders |

## Not included yet
Route filtering, saved routes and push notifications.
