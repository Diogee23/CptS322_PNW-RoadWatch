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
| `MapView.jsx` | The map component (default export) |
| `MapView.css` | Pin, banner and popup styles |
| `models.js` | `Location` and `Alert` classes (from our class diagram) |
| `AlertDatabase.js` | Holds the latest alerts, offline cache, `isStale()` |
| `mockAlerts.js` | Sample alerts for testing without the backend |
| `us-states.json` | State boundary data used for the borders |

## Setup
1. In your React (Vite) project, install the packages the map needs:
   ```bash
   npm install leaflet react-leaflet @turf/union
   ```
   If you get a peer dependency error (`ERESOLVE`) and your project uses React 18, use `npm install leaflet react-leaflet@4 @turf/union` instead.
2. Copy this folder's files into your project's `src` (keep them together in one folder).
3. Use the component. The parent element must have a set height, because the map fills its parent:
   ```jsx
   import MapView from "./map/MapView";

   export default function App() {
     return (
       <div style={{ height: "100vh" }}>
         <MapView useMock />
       </div>
     );
   }
   ```
4. Run `npm run dev` and open the `localhost` link it prints.

You should see the three states with four sample pins. Click a pin for details.

## Not included yet
Directions and route display, route filtering, saved routes and push notifications.
`Alert.intersects(route)` and `AlertDatabase.getByRoute()` are placeholders until the backend can return route geometry.
