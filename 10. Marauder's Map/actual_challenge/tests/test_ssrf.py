def post_owl(client, address):
    resp = client.post("/api/owl", json={"address": address})
    return resp, resp.get_json()


def test_owl_requires_address(web_client):
    resp, data = post_owl(web_client, "")
    assert resp.status_code == 400
    assert data["success"] is False


def test_owl_rejects_missing_scheme(web_client):
    resp, data = post_owl(web_client, "map-internal/archive")
    assert data["success"] is False
    assert resp.status_code == 400


def test_owl_blocks_loopback_literal(web_client):
    resp, data = post_owl(web_client, "http://127.0.0.1:5001/archive")
    assert data["success"] is False
    assert resp.status_code == 403


def test_owl_blocks_localhost_literal(web_client):
    resp, data = post_owl(web_client, "http://localhost:5001/archive")
    assert data["success"] is False
    assert resp.status_code == 403


def test_owl_does_not_block_internal_hostname_string(web_client):
    """The blocklist is naive: it must NOT contain 'map-internal' or this
    whole challenge stops being an SSRF. This only checks the address
    isn't rejected by the blocklist -- it will still fail to *connect*
    here, since there's no live map-internal service reachable from
    this isolated unit-test process."""
    resp, data = post_owl(web_client, "http://map-internal:5001/archive")
    assert resp.status_code != 403


def test_owl_malformed_json_does_not_crash(web_client):
    resp = web_client.post("/api/owl", data="not json", content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
