"""Guards against the import cycle that previously prevented `import app` from
working at all (app.dependencies <-> app.services.authentication)."""

import importlib
import subprocess
import sys
from pathlib import Path


def test_importing_app_does_not_raise_import_error():
    import app  # noqa: F401

    assert app.app is not None


def test_app_factory_module_imports_cleanly():
    module = importlib.import_module("app.main_app")
    assert hasattr(module, "create_app")


def test_dependencies_and_services_do_not_import_each_other_in_a_cycle():
    """app.dependencies must not be what services.authentication imports for
    DBSession - that edge created the cycle."""
    source = Path("app/services/authentication.py").read_text()
    assert "from app.dependencies import" not in source
    assert "from app.database import DBSession" in source


def test_full_app_import_in_a_fresh_interpreter():
    """The real regression test: a cold `import app` in a clean process."""
    result = subprocess.run(
        [sys.executable, "-c", "import app; print(app.app.title)"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "MPSC 50 Years Alumni API" in result.stdout


def test_every_router_is_registered():
    import app

    paths = app.app.openapi()["paths"]
    for path in (
        "/auth/register",
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/admin/alumnae",
        "/payments/initiate",
        "/public/event",
        "/public/statistics",
    ):
        assert path in paths, f"{path} is not registered"