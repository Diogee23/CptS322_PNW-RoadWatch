/*
 * PNW RoadWatch map: plain JavaScript version for the GitHub Pages site.
 * Needs Leaflet (global L) and Turf (global turf) loaded before this file.
 * Class names follow the team class diagram: Location, Alert, AlertDatabase, MapView.
 */
(function () {
  const REFRESH_MS = 60000;                 // refresh alerts every 60 s
  const STALE_MS = 10 * 60000;              // warn when data is older than 10 min
  const PNW_CENTER = [45.5, -118.0];
  const PNW_BOUNDS = [[40.8, -126.0], [50.0, -109.8]];
  const MIN_ZOOM = 6;
  const MAX_ZOOM = 18;
  const STATES_URL = "code/map/us-states.json";   // relative to index.html
  const CACHE_KEY = "pnw-roadwatch:alerts";
  const GLYPH = { low: "i", moderate: "!", high: "!!", critical: "\u26D4" };

  const escapeHtml = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (iso) => new Date(iso).toLocaleString();
  const ago = (m) => new Date(Date.now() - m * 60000).toISOString();

  // Sample alerts, used until the backend serves GET /api/alerts
  const MOCK_ALERTS = [
    { alertID: "wa-1", alertType: "Snow", severity: "high", description: "Chains required on I-90 westbound at Snoqualmie Pass.",
      location: { latitude: 47.4244, longitude: -121.4173 }, sourceAgency: "WA DOT", lastUpdated: ago(3) },
    { alertID: "wa-2", alertType: "Crash", severity: "moderate", description: "Right lane blocked on US-195 near Colfax.",
      location: { latitude: 46.8806, longitude: -117.3636 }, sourceAgency: "WA DOT", lastUpdated: ago(8) },
    { alertID: "or-1", alertType: "Ice", severity: "critical", description: "Black ice, I-84 closed both directions near Pendleton.",
      location: { latitude: 45.6721, longitude: -118.7886 }, sourceAgency: "OR DOT", lastUpdated: ago(1) },
    { alertID: "id-1", alertType: "Construction", severity: "low", description: "Single-lane alternating traffic on US-95 near Moscow.",
      location: { latitude: 46.7324, longitude: -117.0002 }, sourceAgency: "ID DOT", lastUpdated: ago(20) },
  ];

  class Location {
    constructor(latitude, longitude) {
      this.latitude = latitude;
      this.longitude = longitude;
    }
  }

  class Alert {
    constructor({ alertID, location, alertType, severity, description, lastUpdated, sourceAgency }) {
      this.alertID = alertID;
      this.location = location;
      this.alertType = alertType;
      this.severity = severity;
      this.description = description;
      this.lastUpdated = lastUpdated;
      this.sourceAgency = sourceAgency;
    }

    // Accepts camelCase or snake_case, nested location or flat latitude/longitude.
    static fromJSON(j) {
      const loc = j.location ?? { latitude: j.latitude, longitude: j.longitude };
      return new Alert({
        alertID: j.alertID ?? j.alert_id ?? j.id,
        location: new Location(loc.latitude, loc.longitude),
        alertType: j.alertType ?? j.alert_type ?? j.type,
        severity: j.severity,
        description: j.description,
        lastUpdated: j.lastUpdated ?? j.last_updated,
        sourceAgency: j.sourceAgency ?? j.source_agency,
      });
    }

    // TODO: route intersection will be done server-side (PostGIS).
    intersects(route) { return false; }
  }

  class AlertDatabase {
    constructor(storageKey = CACHE_KEY) {
      this.storageKey = storageKey;
      this.alerts = [];
      this.lastRefreshed = null;
      try {
        const c = JSON.parse(localStorage.getItem(this.storageKey));
        if (c) { this.alerts = c.alerts.map(Alert.fromJSON); this.lastRefreshed = c.lastRefreshed; }
      } catch (e) { /* no usable cache */ }
    }
    update(alerts) {
      this.alerts = alerts;
      this.lastRefreshed = Date.now();
      try {
        localStorage.setItem(this.storageKey, JSON.stringify({ alerts, lastRefreshed: this.lastRefreshed }));
      } catch (e) { /* storage blocked or full */ }
    }
    getAll() { return this.alerts; }
    getByRoute(route) { return this.alerts.filter((a) => a.intersects(route)); }
    isStale(now = Date.now()) { return this.lastRefreshed !== null && now - this.lastRefreshed > STALE_MS; }
  }

  class MapView {
    /**
     * @param {string} containerId  id of the div that holds the map
     * @param {object} options      { apiUrl, useMock, onAlertSelect }
     */
    constructor(containerId, options = {}) {
      this.options = Object.assign({ apiUrl: "/api/alerts", useMock: false, onAlertSelect: null }, options);
      this.db = new AlertDatabase();
      this.fetchFailed = false;

      this.map = L.map(containerId, {
        center: PNW_CENTER, zoom: MIN_ZOOM, minZoom: MIN_ZOOM, maxZoom: MAX_ZOOM,
        maxBounds: PNW_BOUNDS, maxBoundsViscosity: 1.0, scrollWheelZoom: true,
      });
      this.zoomLevel = this.map.getZoom();
      this.map.on("zoomend", () => { this.zoomLevel = this.map.getZoom(); });

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        bounds: PNW_BOUNDS, noWrap: true,
      }).addTo(this.map);

      this.pinLayer = L.layerGroup().addTo(this.map);
      this.banner = document.createElement("div");
      this.banner.className = "map-banner";
      this.banner.setAttribute("role", "status");
      this.banner.hidden = true;
      this.map.getContainer().appendChild(this.banner);

      this.drawRegion();
      this.showPins(this.db.getAll());   // cached alerts, if any
      this.refresh();
      setInterval(() => this.refresh(), REFRESH_MS);
      setInterval(() => this.updateBanner(), 30000);
    }

    zoomIn() { this.map.zoomIn(); }
    zoomOut() { this.map.zoomOut(); }

    showPins(alerts) {
      this.pinLayer.clearLayers();
      alerts.forEach((a) => {
        const icon = L.divIcon({
          className: "",
          html: `<div class="alert-pin sev-${escapeHtml(a.severity)}"><span>${GLYPH[a.severity] || "!"}</span></div>`,
          iconSize: [30, 30], iconAnchor: [15, 30], popupAnchor: [0, -28],
        });
        const popup = `<div class="alert-popup">
          <h3>${escapeHtml(a.alertType)}</h3>
          <p>${escapeHtml(a.description)}</p>
          <dl>
            <dt>Severity</dt><dd>${escapeHtml(a.severity)}</dd>
            <dt>Location</dt><dd>${a.location.latitude.toFixed(4)}, ${a.location.longitude.toFixed(4)}</dd>
            <dt>Updated</dt><dd>${escapeHtml(fmt(a.lastUpdated))}</dd>
            <dt>Source</dt><dd>${escapeHtml(a.sourceAgency)}</dd>
          </dl></div>`;
        const marker = L.marker([a.location.latitude, a.location.longitude], { icon }).bindPopup(popup);
        marker.on("click", () => { if (this.options.onAlertSelect) this.options.onAlertSelect(a); });
        marker.addTo(this.pinLayer);
      });
    }

    async refresh() {
      try {
        let raw = MOCK_ALERTS;
        if (!this.options.useMock) {
          const res = await fetch(this.options.apiUrl);
          if (!res.ok) throw new Error("HTTP " + res.status);
          raw = await res.json();
        }
        this.db.update(raw.map(Alert.fromJSON));
        this.showPins(this.db.getAll());
        this.fetchFailed = false;
      } catch (e) {
        this.fetchFailed = true;   // keep whatever pins are already showing
      }
      this.updateBanner();
    }

    updateBanner() {
      const offline = this.fetchFailed && !navigator.onLine;
      const stale = this.db.isStale();
      if (!(offline || stale || this.fetchFailed)) { this.banner.hidden = true; return; }
      this.banner.className = "map-banner" + (offline ? " offline" : "");
      this.banner.textContent = offline
        ? "You're offline. Showing saved alerts" + (this.db.lastRefreshed ? " (last updated " + fmt(this.db.lastRefreshed) + ")." : ".")
        : "Data may be outdated. We couldn't reach the latest alert feed.";
      this.banner.hidden = false;
    }

    // State borders, outline around the whole region, and dimming outside it.
    async drawRegion() {
      try {
        const res = await fetch(STATES_URL);
        if (!res.ok) throw new Error("HTTP " + res.status);
        const all = await res.json();
        const states = all.features.filter((f) => ["Washington", "Oregon", "Idaho"].includes(f.properties.name));
        const outline = states.reduce((acc, f) => (acc ? turf.union(acc, f) : f), null);

        // Dimming: a huge rectangle with the merged region cut out (GeoJSON is [lng, lat]; Leaflet wants [lat, lng]).
        const polys = outline.geometry.type === "Polygon" ? [outline.geometry.coordinates] : outline.geometry.coordinates;
        const holes = polys.map((p) => p[0].map(([lng, lat]) => [lat, lng]));
        const world = [[-85, -180], [-85, 180], [85, 180], [85, -180]];

        L.polygon([world, ...holes], { stroke: false, fillColor: "#3a3a3a", fillOpacity: 0.55, interactive: false }).addTo(this.map);
        L.geoJSON(states, { style: { color: "#a6a6a6", weight: 3, fill: false }, interactive: false }).addTo(this.map);
        L.geoJSON(outline, { style: { color: "#2b2b2b", weight: 4, fill: false }, interactive: false }).addTo(this.map);
      } catch (e) {
        console.error("Could not draw the state borders:", e);
      }
    }
  }

  window.MapView = MapView;

  // Start the map automatically in <div id="mapViewContainer">.
  // Change useMock to false once the backend serves /api/alerts.
  if (document.getElementById("mapViewContainer")) {
    window.roadwatchMap = new MapView("mapViewContainer", { useMock: true });
  }
})();
