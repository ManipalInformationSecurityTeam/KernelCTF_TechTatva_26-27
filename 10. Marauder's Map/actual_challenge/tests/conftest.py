import importlib.util
import os

import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
INTERNAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "map-internal"))


def _load_module(unique_name, file_path):
    """Load a module under a name that can never collide with the other
    app's module (both apps are literally called app.py)."""
    spec = importlib.util.spec_from_file_location(unique_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def web_client(tmp_path):
    """A Flask test client for backend/app.py, backed by a freshly seeded
    temp SQLite DB (never touches the real castle.db)."""
    seed_module = _load_module("marauders_backend_seed", os.path.join(BACKEND_DIR, "seed.py"))

    db_path = str(tmp_path / "castle.db")
    seed_module.DB_PATH = db_path
    seed_module.seed()

    app_module = _load_module("marauders_backend_app", os.path.join(BACKEND_DIR, "app.py"))
    app_module.DB_PATH = db_path

    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture()
def internal_client():
    """A Flask test client for map-internal/app.py."""
    app_module = _load_module("marauders_internal_app", os.path.join(INTERNAL_DIR, "app.py"))
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()
