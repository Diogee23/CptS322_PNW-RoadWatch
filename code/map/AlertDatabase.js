import { Alert } from "./models";

const STALE_MS = 10 * 60_000; // Warn when data is older than 10 minutes

// Frontend copy of AlertDatabase: holds the latest alerts and persists
// them in the browser so they can be shown offline
export class AlertDatabase {
  constructor(storageKey = "pnw-roadwatch:alerts") {
    this.storageKey = storageKey;
    this.alerts = [];          // List<Alert>
    this.lastRefreshed = null; // ms timestamp
    this._loadCache();
  }

  update(alerts) {
    this.alerts = alerts;
    this.lastRefreshed = Date.now();
    try {
      localStorage.setItem(this.storageKey, JSON.stringify({ alerts, lastRefreshed: this.lastRefreshed }));
    } catch { /* storage blocked or full */ }
  }

  getAll() { return this.alerts; }

  getByRoute(route) { return this.alerts.filter((a) => a.intersects(route)); }

  isStale(now = Date.now()) {
    return this.lastRefreshed !== null && now - this.lastRefreshed > STALE_MS;
  }

  _loadCache() {
    try {
      const c = JSON.parse(localStorage.getItem(this.storageKey));
      if (c) {
        this.alerts = c.alerts.map(Alert.fromJSON);
        this.lastRefreshed = c.lastRefreshed;
      }
    } catch { /* no usable cache */ }
  }
}
