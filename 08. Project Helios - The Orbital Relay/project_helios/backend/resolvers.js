const { users, satellites, relays, telemetryPackets, generateSatelliteId } = require("./db");

const resolvers = {
  Query: {
    async me(_, __, { user }) {
      if (!user) throw new Error("401: Unauthorized");
      return users[user.id];
    },
    async satelliteInfo(_, { id }, { user }) {
      if (!user) throw new Error("401: Unauthorized");
      const satellite = satellites.find(s => s.id === id);
      if (!satellite) return null;
      
      // The Front Door Block
      if (satellite.classification === "MILITARY") {
        throw new Error("403: Forbidden - Military clearance required to view HELIOS-4 telemetry");
      }
      return satellite;
    },
  },
  Mutation: {
    async launchCubeSat(_, { designation }, { user }) {
      if (!user) throw new Error("401: Unauthorized");
      const newSat = {
        id: generateSatelliteId(),
        designation: designation.trim(),
        ownerId: user.id,
        classification: "CIVILIAN",
      };
      satellites.push(newSat);
      users[user.id].relaySlots += 1;
      return newSat;
    },
    async establishRelayConnection(_, { sourceSatId, targetSatId }, { user }) {
      if (!user) throw new Error("401: Unauthorized");
      
      const source = satellites.find(s => s.id === sourceSatId);
      if (!source || source.ownerId !== user.id) throw new Error("403: Unauthorized on source asset.");
      
      const target = satellites.find(s => s.id === targetSatId);
      if (!target) throw new Error("404: Target satellite not found");
      
      // VULNERABILITY: Missing Target Authorization Check
      relays.push({ fromId: sourceSatId, toId: targetSatId });
      return source;
    },
    async requestClearanceUpgrade(_, { level }) {
      return "Error: Endpoint deprecated. Contact Sector 4 administrator.";
    }
  },
  Satellite: {
    async telemetryData(satellite) {
      // VULNERABILITY: Nested Resolver Trust
      return telemetryPackets.filter(p => p.satelliteId === satellite.id);
    },
    async relayConnections(satellite) {
      // VULNERABILITY: Nested Resolver Trust
      const targetIds = relays.filter(r => r.fromId === satellite.id).map(r => r.toId);
      return satellites.filter(s => targetIds.includes(s.id));
    },
  },
  User: {
    async mySatellites(userObj) {
      return satellites.filter(s => s.ownerId === userObj.id);
    },
  },
};

module.exports = resolvers;
