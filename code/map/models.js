// Frontend classes

export class Location {
  constructor(latitude, longitude) {
    this.latitude = latitude;     // double
    this.longitude = longitude;   // double
  }
}

export class Alert {
  constructor({ alertID, location, alertType, severity, description, lastUpdated, sourceAgency }) {
    this.alertID = alertID;               // string
    this.location = location;             // Location
    this.alertType = alertType;           // string
    this.severity = severity;             // "low" | "moderate" | "high" | "critical"
    this.description = description;       // string
    this.lastUpdated = lastUpdated;       // date (ISO string from the API)
    this.sourceAgency = sourceAgency;     // "WADOT" | "ORDOT" | "IDDOT"
  }

  // Accepts the backend's JSON
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

  // TODO: route intersection is done server-side (PostGIS)
  // Implement this once the backend returns route geometry
  intersects(route) {
    return false;
  }
}
