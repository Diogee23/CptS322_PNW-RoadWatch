import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, Polygon, Circle, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./MapView.css";
import { Alert } from "./models";
import { AlertDatabase } from "./AlertDatabase";
import { mockAlerts } from "./mockAlerts";
import usStates from "./us-states.json";
import union from "@turf/union";

// Keep only the three states we cover (WA, OR, ID) for the map
const PNW_STATES = {
  type: "FeatureCollection",
  features: usStates.features.filter((f) =>
    ["Washington", "Oregon", "Idaho"].includes(f.properties.name)
  ),
};

// Merge the three states into one shape so we can outline the whole region
const PNW_OUTLINE = union({
  type: "FeatureCollection",
  features: PNW_STATES.features,
});

// Dim everything outside the three states: a huge rectangle with the region cut out
const WORLD_RING = [[-85, -180], [-85, 180], [85, 180], [85, -180]];
const outlineGeometry = PNW_OUTLINE.geometry;
const outlinePolygons = outlineGeometry.type === "Polygon" ? [outlineGeometry.coordinates] : outlineGeometry.coordinates;

const REGION_HOLES = outlinePolygons.map((p) => p[0].map(([lng, lat]) => [lat, lng]));
const DIM_MASK = [WORLD_RING, ...REGION_HOLES];

const REFRESH_MS = 60_000;
const PNW_CENTER = [45.5, -118.0];  // WA / OR / ID

// Restrict the map to the Pacific Northwest region (WA, OR, ID) plus a small margin
const PNW_BOUNDS = [[40.8, -126.0], [50.0, -109.8]];
const MIN_ZOOM = 6;   // Can't zoom out to see the whole world
const MAX_ZOOM = 18;

const GLYPH = { low: "i", moderate: "!", high: "!!", critical: "⛔" };

const pinIcon = (severity) =>
  L.divIcon({
    className: "",
    html: `<div class="alert-pin sev-${severity}"><span>${GLYPH[severity] ?? "!"}</span></div>`,
    iconSize: [30, 30], iconAnchor: [15, 30], popupAnchor: [0, -28],
  });

// "You are here" marker: a blue dot with a white ring
const userIcon = L.divIcon({
  className: "",
  html: '<div class="user-dot"></div>',
  iconSize: [18, 18], iconAnchor: [9, 9],
});

const GEO_OPTIONS = { enableHighAccuracy: true, maximumAge: 10_000, timeout: 20_000 };
const LOCATE_ZOOM = 12;

const fmt = (iso) => new Date(iso).toLocaleString();

function ZoomTracker({ onZoom }) {
  useMapEvents({ zoomend: (e) => onZoom(e.target.getZoom()) });
  return null;
}

/*
 * MapView: -zoomLevel, +zoomIn(), +zoomOut(), +showPins(alerts)
 * Other components can call these through a ref:  const map = useRef(); <MapView ref={map} />
 */
const MapView = forwardRef(function MapView(
  { apiUrl = "/api/alerts", useMock = false, onAlertSelect, center = PNW_CENTER, initialZoom = 6 },
  ref
) {
  const leafletMap = useRef(null);
  const db = useRef(new AlertDatabase());
  const [alerts, setAlerts] = useState(() => db.current.getAll());
  const [zoomLevel, setZoomLevel] = useState(initialZoom);
  const [fetchFailed, setFetchFailed] = useState(false);
  const [now, setNow] = useState(Date.now());

  const [userPos, setUserPos] = useState(null);     // { lat, lng, accuracy } or null
  const [locating, setLocating] = useState(false);
  const [geoMessage, setGeoMessage] = useState(null);
  const watchId = useRef(null);
  const pendingCenter = useRef(false);               // recenter on the next fix

  const showPins = useCallback((list) => setAlerts(list), []);
  const zoomIn = useCallback(() => leafletMap.current?.zoomIn(), []);
  const zoomOut = useCallback(() => leafletMap.current?.zoomOut(), []);

  // Move the map to the user, unless they're outside the region the map is locked to
  const centerOnUser = useCallback((pos) => {
    const map = leafletMap.current;
    if (!map) return;
    if (!L.latLngBounds(PNW_BOUNDS).contains([pos.lat, pos.lng])) {
      setGeoMessage("Your location is outside the WA / OR / ID area this map covers.");
      return;
    }
    map.flyTo([pos.lat, pos.lng], Math.max(map.getZoom(), LOCATE_ZOOM));
  }, []);

  const stopWatching = useCallback(() => {
    if (watchId.current !== null) {
      navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
    }
  }, []);

  // Ask for permission (first call), then keep the dot updated as the user moves
  const locate = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setGeoMessage("Location isn't supported by this browser.");
      return;
    }
    setGeoMessage(null);
    if (userPos) { centerOnUser(userPos); return; }
    pendingCenter.current = true;
    if (watchId.current !== null) return; // already waiting for the first fix
    setLocating(true);
    watchId.current = navigator.geolocation.watchPosition(
      ({ coords }) => {
        const pos = { lat: coords.latitude, lng: coords.longitude, accuracy: coords.accuracy };
        setUserPos(pos);
        setLocating(false);
        if (pendingCenter.current) { pendingCenter.current = false; centerOnUser(pos); }
      },
      (err) => {
        setLocating(false);
        pendingCenter.current = false;
        if (err.code === err.PERMISSION_DENIED) {
          stopWatching();
          setGeoMessage("Location access was blocked. Allow it in your browser's site settings to see where you are.");
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          setGeoMessage("Your location is unavailable right now.");
        } else {
          setGeoMessage("Finding your location timed out. Still trying…");
        }
      },
      GEO_OPTIONS
    );
  }, [userPos, centerOnUser, stopWatching]);

  useEffect(() => stopWatching, [stopWatching]); // stop tracking on unmount

  useImperativeHandle(ref, () => ({ zoomIn, zoomOut, showPins, locate, get zoomLevel() { return zoomLevel; } }), [zoomIn, zoomOut, showPins, locate, zoomLevel]);

  const refresh = useCallback(async () => {
    try {
      let raw = mockAlerts;
      if (!useMock) {
        const res = await fetch(apiUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        raw = await res.json();
      }
      const list = raw.map(Alert.fromJSON);
      db.current.update(list);
      showPins(db.current.getAll());
      setFetchFailed(false);
    } catch {
      setFetchFailed(true); // Keep whatever pins (live or cached) are already showing
    }
  }, [apiUrl, useMock, showPins]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  const offline = fetchFailed && !navigator.onLine;
  const stale = db.current.isStale(now);

  return (
    <div className="map-view">
      {(offline || stale || fetchFailed) && (
        <div className={`map-banner ${offline ? "offline" : ""}`} role="status">
          {offline
            ? `You're offline. Showing saved alerts${db.current.lastRefreshed ? ` (last updated ${fmt(db.current.lastRefreshed)})` : ""}.`
            : "Data may be outdated. We couldn't reach the latest alert feed."}
        </div>
      )}
      <button type="button" className={`locate-btn${userPos ? " active" : ""}`} onClick={locate}
              disabled={locating} aria-label="Show my location" title="Show my location">
        {locating ? "…" : "◎"}
      </button>
      {geoMessage && (
        <div className="map-banner geo-msg" role="status">
          {geoMessage}
          <button type="button" className="geo-close" onClick={() => setGeoMessage(null)} aria-label="Dismiss">×</button>
        </div>
      )}
      <MapContainer ref={leafletMap} center={center} zoom={initialZoom} minZoom={MIN_ZOOM} maxZoom={MAX_ZOOM} maxBounds={PNW_BOUNDS} 
       maxBoundsViscosity={1.0} scrollWheelZoom>
       <ZoomTracker onZoom={setZoomLevel} />
       <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        bounds={PNW_BOUNDS}
        noWrap
      />
      <Polygon
       positions={DIM_MASK}
       interactive={false}
       pathOptions={{ stroke: false, fillColor: "#5f5f5f", fillOpacity: 0.35 }}
      />
      <GeoJSON
       data={PNW_STATES}
       interactive={false}
       style={{ color: "#a6a6a6", weight: 3, fill: false }}
      />
      <GeoJSON
       data={PNW_OUTLINE}
       interactive={false}
       style={{ color: "#2b2b2b", weight: 4, fill: false }}
      />
        {userPos && (
          <>
            <Circle center={[userPos.lat, userPos.lng]} radius={userPos.accuracy} interactive={false}
                    pathOptions={{ color: "#1a73e8", weight: 1, fillColor: "#1a73e8", fillOpacity: 0.12 }} />
            <Marker position={[userPos.lat, userPos.lng]} icon={userIcon} interactive={false} zIndexOffset={1000} />
          </>
        )}
        {alerts.map((a) => (
          <Marker key={a.alertID} position={[a.location.latitude, a.location.longitude]}
                  icon={pinIcon(a.severity)} eventHandlers={{ click: () => onAlertSelect?.(a) }}>
            <Popup>
              <div className="alert-popup">
                <h3>{a.alertType}</h3>
                <p>{a.description}</p>
                <dl>
                  <dt>Severity</dt><dd>{a.severity}</dd>
                  <dt>Location</dt><dd>{a.location.latitude.toFixed(4)}, {a.location.longitude.toFixed(4)}</dd>
                  <dt>Updated</dt><dd>{fmt(a.lastUpdated)}</dd>
                  <dt>Source</dt><dd>{a.sourceAgency}</dd>
                </dl>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
});

export default MapView;