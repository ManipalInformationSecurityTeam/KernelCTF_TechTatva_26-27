FLAG = "kernel{7h3_m4p_r3m3mb3rs_wh4t_y0u_h1d3}"


def test_index_route(internal_client):
    resp = internal_client.get("/")
    assert resp.status_code == 200


def test_people_route_has_no_flag(internal_client):
    resp = internal_client.get("/people")
    assert resp.status_code == 200
    assert FLAG not in resp.get_data(as_text=True)


def test_archive_route_lists_room_of_requirement(internal_client):
    resp = internal_client.get("/archive")
    assert resp.status_code == 200
    assert "room-of-requirement" in resp.get_data(as_text=True)


def test_room_of_requirement_requires_phrase(internal_client):
    resp = internal_client.get("/archive/room-of-requirement")
    assert resp.status_code == 400
    assert FLAG not in resp.get_data(as_text=True)


def test_room_of_requirement_rejects_wrong_phrase(internal_client):
    resp = internal_client.get("/archive/room-of-requirement?phrase=open+sesame")
    assert resp.status_code == 403
    assert FLAG not in resp.get_data(as_text=True)


def test_room_of_requirement_accepts_correct_phrase(internal_client):
    resp = internal_client.get("/archive/room-of-requirement?phrase=mischief managed")
    assert resp.status_code == 200
    assert FLAG in resp.get_data(as_text=True)


def test_room_of_requirement_phrase_is_case_insensitive(internal_client):
    resp = internal_client.get("/archive/room-of-requirement?phrase=MISCHIEF MANAGED")
    assert resp.status_code == 200
    assert FLAG in resp.get_data(as_text=True)
