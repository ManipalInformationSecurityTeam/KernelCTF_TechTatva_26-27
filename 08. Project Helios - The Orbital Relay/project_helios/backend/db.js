// Astraeus Primary In-Memory Store
const users = {
  "USER-001": { id: "USER-001", username: "Dr. Aris (Manipal University)", accountTier: "CIVILIAN", relaySlots: 0 },
  "SYSTEM": { id: "SYSTEM", username: "Astraeus Command", accountTier: "MILITARY", relaySlots: 999 },
};

const satellites = [
  { id: "HELIOS-4", designation: "HELIOS-4 [CLASSIFIED]", ownerId: "SYSTEM", classification: "MILITARY" },
  { id: "NOAA-9", designation: "NOAA Weather Relay", ownerId: "SYSTEM", classification: "CIVILIAN" }
];

const relays = [];

const telemetryPackets = [
  { satelliteId: "HELIOS-4", sensorType: "Thermal", rawData: "Outer Hull: 120C" },
  { satelliteId: "HELIOS-4", sensorType: "Radiation", rawData: "Solar Flux: 4.22mSv" },
  { satelliteId: "HELIOS-4", sensorType: "Encrypted_Uplink", rawData: "kernel{0rb1t4l_n3tw0rk_byp4ss_c0mpr0m1s3d}" },
  { satelliteId: "HELIOS-4", sensorType: "Gyroscope", rawData: "Pitch: 12.4, Yaw: 0.1, Roll: -0.3" },
  { satelliteId: "NOAA-9", sensorType: "Atmospheric", rawData: "Humidity: 88%, Pressure: 1012hPa" },
];

function generateSatelliteId() {
  return `CUBE-${String(Math.floor(Math.random() * 10000)).padStart(4, "0")}`;
}

function authenticateToken(token) {
  if (token === "student_civilian_token") return users["USER-001"];
  return null;
}

module.exports = { users, satellites, relays, telemetryPackets, generateSatelliteId, authenticateToken };
