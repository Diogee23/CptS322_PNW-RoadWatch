import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./MapView.css";
import { Alert } from "./models";
import { AlertDatabase } from "./AlertDatabase";
import { mockAlerts } from "./mockAlerts";
import usStates from "./us-states.json";

// Keep only the three states we cover (WA, OR, ID) for the map
const PNW_STATES = {
  type: "FeatureCollection",
  features: usStates.features.filter((f) =>
    ["Washington", "Oregon", "Idaho"].includes(f.properties.name)
  ),
};

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

  const showPins = useCallback((list) => setAlerts(list), []);
  const zoomIn = useCallback(() => leafletMap.current?.zoomIn(), []);
  const zoomOut = useCallback(() => leafletMap.current?.zoomOut(), []);
  useImperativeHandle(ref, () => ({ zoomIn, zoomOut, showPins, get zoomLevel() { return zoomLevel; } }), [zoomIn, zoomOut, showPins, zoomLevel]);

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
      <MapContainer ref={leafletMap} center={center} zoom={initialZoom} minZoom={MIN_ZOOM} maxZoom={MAX_ZOOM} maxBounds={PNW_BOUNDS} 
       maxBoundsViscosity={1.0} scrollWheelZoom>
       <ZoomTracker onZoom={setZoomLevel} />
       <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        bounds={PNW_BOUNDS}
        noWrap
      />
      <GeoJSON
       data={PNW_STATES}
       interactive={false}
       style={{ color: "#1b5e4b", weight: 3, fill: false }}
      />
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
