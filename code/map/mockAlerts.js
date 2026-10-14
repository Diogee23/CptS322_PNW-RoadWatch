// Sample data for the map until the backend serves GET /api/alerts
const ago = (m) => new Date(Date.now() - m * 60000).toISOString();

export const mockAlerts = [
  { alertID: "wa-1", alertType: "Snow", severity: "high", description: "Chains required on I-90 westbound at Snoqualmie Pass.",
    location: { latitude: 47.4244, longitude: -121.4173 }, sourceAgency: "WA DOT", lastUpdated: ago(3) },
  { alertID: "wa-2", alertType: "Crash", severity: "moderate", description: "Right lane blocked on US-195 near Colfax.",
    location: { latitude: 46.8806, longitude: -117.3636 }, sourceAgency: "WA DOT", lastUpdated: ago(8) },
  { alertID: "or-1", alertType: "Ice", severity: "critical", description: "Black ice, I-84 closed both directions near Pendleton.",
    location: { latitude: 45.6721, longitude: -118.7886 }, sourceAgency: "OR DOT", lastUpdated: ago(1) },
  { alertID: "id-1", alertType: "Construction", severity: "low", description: "Single-lane alternating traffic on US-95 near Moscow.",
    location: { latitude: 46.7324, longitude: -117.0002 }, sourceAgency: "ID DOT", lastUpdated: ago(20) },
];
