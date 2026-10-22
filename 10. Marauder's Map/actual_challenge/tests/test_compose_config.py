import os

import yaml

COMPOSE_PATH = os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")


def _load_compose():
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


def test_map_internal_service_defined_with_correct_name_and_port():
    cfg = _load_compose()
    services = cfg["services"]
    assert "map-internal" in services, "service must be named 'map-internal' so it resolves as that hostname"
    svc = services["map-internal"]
    assert svc.get("expose") == ["5001"], "internal service must expose port 5001"


def test_map_internal_service_has_no_published_host_port():
    cfg = _load_compose()
    svc = cfg["services"]["map-internal"]
    assert "ports" not in svc, "map-internal must NOT publish a host port (no 'ports:' key)"


def test_map_internal_on_shared_network_with_web():
    cfg = _load_compose()
    services = cfg["services"]
    web_nets = set(services["web"].get("networks", []))
    internal_nets = set(services["map-internal"].get("networks", []))
    assert web_nets & internal_nets, "web and map-internal must share a network"


def test_web_service_publishes_port_5000():
    cfg = _load_compose()
    svc = cfg["services"]["web"]
    assert any("5000:5000" in p for p in svc.get("ports", []))


def test_web_build_context_includes_both_frontend_and_backend():
    cfg = _load_compose()
    build = cfg["services"]["web"]["build"]
    assert build["context"] == "."
    assert build["dockerfile"] == "backend/Dockerfile"
