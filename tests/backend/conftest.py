import sys
from pathlib import Path

import pytest

# Let the tests import app.py, fetchers.py, normalize.py from code/backend
BACKEND = Path(__file__).resolve().parents[2] / "code" / "backend"
sys.path.insert(0, str(BACKEND))

import app as app_module  # noqa: E402


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    """Every test starts with no API keys (sample mode) and an empty cache."""
    for var in ("WA_API_KEY", "OR_API_KEY", "ID_API_KEY", "USE_SAMPLE_DATA"):
        monkeypatch.delenv(var, raising=False)
    app_module.clear_cache()
    yield
    app_module.clear_cache()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()
