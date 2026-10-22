# Deployment guide

## Requirements on the host

- Docker with Compose v2
- `bash`, `curl`, and `python3` (used by `deploy.sh`)

## Deploy

From the `challenge/` folder:

```
bash deploy.sh                # builds, starts, verifies. Serves on port 8080
PORT=9000 bash deploy.sh      # another port
bash teardown.sh              # stop and remove everything
```

`deploy.sh` prints `DEPLOYED` only if the full five-step chain passes against the running
containers. Players connect to `http://<server-address>:<PORT>`.

## Important

- The diagnostics service is not published. Keep it that way. Its shell is the reason
  shard 3 is isolated from the gateway's files.
- The Docker files have not been run in the build environment. The first deployment should
  be watched. A failure shows up as a non-`DEPLOYED` result from `deploy.sh`, with logs from
  `docker compose logs`.
- Set the public address in the player description before the event.

## Reverse proxy and X-Forwarded-For (read before deploying)

Step 1 of the challenge depends on the gateway reading the `X-Forwarded-For` header. The
gateway takes the **first** address in that header and admits the request if it is `127.0.0.1`.

If you put a reverse proxy, load balancer, or CDN in front of the containers, configure it to
**append** to `X-Forwarded-For`, not overwrite it. Examples:

- nginx: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` (appends)
- Traefik, Caddy, and most load balancers: keep the incoming header and add the client address after it.

Do **not** use an option that replaces the header with the client's real address (for example
nginx `proxy_set_header X-Forwarded-For $remote_addr;`). That makes Step 1 impossible.

Test after any proxy change: `curl -H "X-Forwarded-For: 127.0.0.1" http://<server>:<PORT>/` must
return the dashboard, not a 403.

## Verify after deploy

From a different machine that has a copy of the full project:

```
python3 solve/solve.py http://<server-address>:<PORT>
```

It must print `PASS`.
