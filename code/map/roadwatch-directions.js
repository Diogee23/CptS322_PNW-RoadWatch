/*
 * PNW RoadWatch directions: draws a route on the Leaflet map and lists
 * step-by-step directions. Load AFTER roadwatch-map.js (needs window.roadwatchMap,
 * Leaflet global L, Turf global turf) and after the Google Maps script.
 *
 * Usage (see main.js):
 *   const directions = new DirectionsController(window.roadwatchMap, document.getElementById("directionsPanel"));
 *   await directions.showRoute(startPlace, endPlace);   // google.maps.places.Place objects
 */
(function () {
  const ROUTE_STYLE = { color: "#1a73e8", weight: 6, opacity: 0.85 };
  const STEP_STYLE = { color: "#ff6d00", weight: 8, opacity: 0.95 };
  const ALERT_NEAR_KM = 2;              // alerts within this distance of the route are listed
  const METERS_PER_MILE = 1609.344;

  const fmtDist = (m) => {
    const mi = m / METERS_PER_MILE;
    return mi >= 0.2 ? mi.toFixed(1) + " mi" : Math.round(m * 3.281 / 10) * 10 + " ft";
  };
  const fmtTime = (ms) => {
    const min = Math.max(1, Math.round(ms / 60000));
    return min < 60 ? min + " min" : Math.floor(min / 60) + " hr " + (min % 60) + " min";
  };

  // Routes library returns LatLngAltitude objects (lat/lng as numbers); be tolerant of functions too
  const toLatLng = (p) => [typeof p.lat === "function" ? p.lat() : p.lat, typeof p.lng === "function" ? p.lng() : p.lng];
  const toLatLngs = (path) => (path || []).map(toLatLng);

  const REGION_STATES = ["WA", "OR", "ID"];

  // True if the place is in Washington, Oregon or Idaho (USA)
  // Checking the country too matters: "WA" is also Western Australia
  const inRegion = (place) => {
  const comps = place.addressComponents || [];
  const find = (type) => comps.find((c) => c.types.includes(type));
  const country = find("country");
  const state = find("administrative_area_level_1");
  return !!country && country.shortText === "US" && !!state && REGION_STATES.includes(state.shortText);};

  class DirectionsController {
    constructor(mapView, panelEl) {
      this.mapView = mapView;
      this.map = mapView.map;
      this.panel = panelEl;
      this.routeLayer = L.layerGroup().addTo(this.map);
      this.stepLayer = L.layerGroup().addTo(this.map);
    }

    clear() {
      this.routeLayer.clearLayers();
      this.stepLayer.clearLayers();
      this.panel.replaceChildren();
    }

    setStatus(text, isError = false) {
      this.panel.replaceChildren();
      const p = document.createElement("p");
      p.className = "dir-status" + (isError ? " error" : "");
      p.textContent = text;
      this.panel.appendChild(p);
    }

    async showRoute(origin, destination) {
      if (!origin || !destination) {
        this.setStatus("Please enter a starting location and a destination.", true);
        return;
      }
      const outside = [];
      if (!inRegion(origin)) outside.push("starting location");
      if (!inRegion(destination)) outside.push("destination");
      if (outside.length) {
        this.clear();   // remove any previous route so it doesn't stay on the map
        const who = outside.length === 2 ? "Your starting location and destination are" : `Your ${outside[0]} is`;
        this.setStatus(`${who} outside Washington, Oregon, and Idaho. Please enter locations within this region.`, true);
        return;
      }
      this.clear();
      this.setStatus("Finding route...");

      try {
        const { Route } = await google.maps.importLibrary("routes");
        const { routes } = await Route.computeRoutes({
          origin,
          destination,
          travelMode: "DRIVING",
          fields: ["path", "legs", "distanceMeters", "durationMillis", "viewport"],
        });
        if (!routes || !routes.length) {
          this.setStatus("No driving route found between those two places.", true);
          return;
        }
        this.render(routes[0]);
      } catch (err) {
        console.error("Directions failed:", err);
        this.setStatus("Couldn't get directions. Check that the Routes API is enabled for your key.", true);
      }
    }

    render(route) {
      const latlngs = toLatLngs(route.path);
      this.routeLayer.clearLayers();
      const line = L.polyline(latlngs, ROUTE_STYLE).addTo(this.routeLayer);
      L.circleMarker(latlngs[0], { radius: 7, color: "#fff", weight: 2, fillColor: "#2e7d32", fillOpacity: 1 }).addTo(this.routeLayer);
      L.circleMarker(latlngs[latlngs.length - 1], { radius: 7, color: "#fff", weight: 2, fillColor: "#c62828", fillOpacity: 1 }).addTo(this.routeLayer);
      this.map.fitBounds(line.getBounds(), { padding: [40, 40] });

      this.panel.replaceChildren();

      // Summary
      const summary = document.createElement("div");
      summary.className = "dir-summary";
      summary.textContent = `${fmtTime(route.durationMillis)} · ${fmtDist(route.distanceMeters)}`;
      this.panel.appendChild(summary);

      // Alerts near the route
      const nearby = this.alertsNear(latlngs);
      const alertBox = document.createElement("div");
      alertBox.className = "dir-alerts" + (nearby.length ? " has-alerts" : "");
      if (nearby.length) {
        const h = document.createElement("strong");
        h.textContent = `${nearby.length} alert${nearby.length > 1 ? "s" : ""} along this route`;
        const ul = document.createElement("ul");
        nearby.forEach((a) => {
          const li = document.createElement("li");
          li.textContent = `${a.severity.toUpperCase()}: ${a.alertType}. ${a.description}`;
          ul.appendChild(li);
        });
        alertBox.append(h, ul);
      } else {
        alertBox.textContent = "No active alerts along this route.";
      }
      this.panel.appendChild(alertBox);

      // Steps
      const ol = document.createElement("ol");
      ol.className = "dir-steps";
      (route.legs || []).forEach((leg) => {
        (leg.steps || []).forEach((step) => {
          const li = document.createElement("li");
          const text = document.createElement("span");
          text.textContent = step.instructions || step.navigationInstruction?.instructions || "Continue";
          const meta = document.createElement("small");
          meta.textContent = fmtDist(step.distanceMeters || 0);
          li.append(text, meta);
          li.tabIndex = 0;
          const focus = () => this.focusStep(step, li, ol);
          li.addEventListener("click", focus);
          li.addEventListener("keydown", (e) => { if (e.key === "Enter") focus(); });
          ol.appendChild(li);
        });
      });
      this.panel.appendChild(ol);

      // Warn if the route leaves the area the map is locked to
      const bounds = L.latLngBounds([[40.8, -126.0], [50.0, -109.8]]);
      if (!latlngs.every((ll) => bounds.contains(ll))) {
        const note = document.createElement("p");
        note.className = "dir-status error";
        note.textContent = "Part of this route is outside the WA / OR / ID area this map covers.";
        this.panel.appendChild(note);
      }
    }

    // Highlight one step on the map and zoom to it
    focusStep(step, li, ol) {
      ol.querySelectorAll("li.active").forEach((el) => el.classList.remove("active"));
      li.classList.add("active");
      this.stepLayer.clearLayers();
      const pts = toLatLngs(step.path);
      if (pts.length > 1) {
        const seg = L.polyline(pts, STEP_STYLE).addTo(this.stepLayer);
        this.map.fitBounds(seg.getBounds(), { padding: [80, 80], maxZoom: 15 });
      }
    }

    // Client-side check for alerts close to the route (server-side PostGIS can replace this later)
    alertsNear(latlngs) {
      if (latlngs.length < 2 || typeof turf === "undefined") return [];
      const line = turf.lineString(latlngs.map(([lat, lng]) => [lng, lat]));
      return this.mapView.db.getAll().filter((a) => {
        const pt = turf.point([a.location.longitude, a.location.latitude]);
        return turf.pointToLineDistance(pt, line, { units: "kilometers" }) <= ALERT_NEAR_KM;
      });
    }
  }

  window.DirectionsController = DirectionsController;
})();
