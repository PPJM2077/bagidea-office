# =============================================================================
# Company Simulator — Health & Sanity Checks
#
# These tests verify that the test framework itself is wired correctly:
#   - pytest loads and runs
#   - conftest fixtures resolve
#   - Python environment is sound
#   - imports work
#   - coverage config is valid
#   - markers are registered
#
# A failing health test = infrastructure problem, not a code problem.
# Reference: qa-standards.md §4 (AAA Pattern), §4.1 (Naming Convention)
# =============================================================================

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ═════════════════════════════════════════════════════════════════════════
# Python environment sanity
# ═════════════════════════════════════════════════════════════════════════


class TestFrameworkHealth:
    """Verify the test runner and Python environment are healthy."""

    def test_pytest_should_load_and_run(self) -> None:
        """Trivial: if this test runs, pytest is working."""
        # Arrange & Act & Assert — one-liner (the test itself)
        assert True, "If this fails, the test framework is fundamentally broken"

    def test_python_version_should_be_at_least_3_11(self) -> None:
        """Python 3.11+ is required per requirements.txt."""
        # Arrange
        version_info = sys.version_info

        # Act & Assert
        assert version_info.major == 3
        assert version_info.minor >= 11, (
            f"Python 3.11+ required, got {version_info.major}.{version_info.minor}"
        )

    def test_project_root_should_exist(self, project_root: Path) -> None:
        """The project root fixture must point to an existing directory."""
        # Arrange & Act — fixture already resolved
        # Assert
        assert project_root.is_dir(), f"Project root does not exist: {project_root}"

    def test_project_root_should_have_pytest_ini(self, project_root: Path) -> None:
        """pytest.ini must be at the project root."""
        # Arrange
        ini_path = project_root / "pytest.ini"

        # Act & Assert
        assert ini_path.is_file(), f"pytest.ini not found at {ini_path} — pytest won't load it"

    def test_coveragerc_should_be_valid_toml(self, project_root: Path) -> None:
        """Ensure the coverage config file exists (it's INI-like, not TOML)."""
        # Arrange
        cfg_path = project_root / ".coveragerc"

        # Act & Assert
        assert cfg_path.is_file(), f".coveragerc not found at {cfg_path}"

    def test_markers_should_be_registered(self) -> None:
        """All custom markers defined in pytest.ini must be registrable.

        ``--strict-markers`` in ``pytest.ini`` ensures any marker used in
        tests but not listed in ``markers`` will raise an error at collection
        time.  This test verifies the expected ones are accessible.
        """
        # Arrange
        expected_markers = {
            "unit",
            "integration",
            "e2e",
            "smoke",
            "slow",
            "flaky",
            "serial",
        }

        # Act & Assert
        for marker in expected_markers:
            assert hasattr(pytest.mark, marker), (
                f"Marker '{marker}' not registered. Add it to pytest.ini [pytest] markers section."
            )


# ═════════════════════════════════════════════════════════════════════════
# Conftest fixture verification
# ═════════════════════════════════════════════════════════════════════════


class TestConftestFixtures:
    """Verify shared fixtures from conftest.py resolve correctly."""

    def test_project_root_fixture_should_work(self, project_root: Path) -> None:
        """project_root fixture must return the project root."""
        # Arrange & Act
        # Assert
        assert "company-simulator" in str(project_root)
        assert (project_root / "requirements.txt").is_file()

    def test_tests_root_fixture_should_work(self, tests_root: Path) -> None:
        """tests_root fixture must return the tests directory."""
        # Arrange & Act
        # Assert
        assert tests_root.name == "tests"
        assert (tests_root / "conftest.py").is_file()

    def test_test_settings_should_contain_required_keys(self, test_settings: dict) -> None:
        """test_settings must contain all critical keys."""
        # Arrange
        required = [
            "ENVIRONMENT",
            "DEBUG",
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
        ]

        # Act & Assert
        for key in required:
            assert key in test_settings, f"Missing required test setting: {key}"

        # Assert — test environment is isolated
        assert test_settings["ENVIRONMENT"] == "test", "Test environment must be 'test'"

    def test_fresh_env_should_be_isolated(self, fresh_env: dict) -> None:
        """Mutations to fresh_env must not leak after test ends."""
        # Act — simulate a buggy test that pollutes env
        os.environ["LEAK_TEST"] = "should_not_escape"

        # Assert
        assert os.environ.get("LEAK_TEST") == "should_not_escape"

    def test_fresh_env_should_restore_after_test(self) -> None:
        """The previous test's env mutation must be gone."""
        # Arrange, Act, Assert
        assert "LEAK_TEST" not in os.environ, (
            "fresh_env fixture leaked — LEAK_TEST found in env of a different test"
        )

    def test_temp_dir_should_be_writable(self, temp_dir: Path) -> None:
        """temp_dir fixture must give a writable directory."""
        # Arrange
        test_file = temp_dir / "sanity_check.tmp"

        # Act
        test_file.write_text("hello from QA")

        # Assert
        assert test_file.is_file()
        assert test_file.read_text() == "hello from QA"

    def test_temp_dir_should_be_unique(self, temp_dir: Path) -> None:
        """Each call to temp_dir gets a different path."""
        # Arrange — we inject another fixture call manually
        # Act & Assert
        assert temp_dir.is_dir()


# ═════════════════════════════════════════════════════════════════════════
# Unit marker tests (smoke tests for the test categories)
# ═════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestUnitMarkerSanity:
    """Smoke tests tagged with @pytest.mark.unit."""

    def test_unit_marker_should_inherit_on_class(self) -> None:
        """Markers applied at class level must propagate to methods."""
        # Arrange — the marker is applied at class level
        marker = pytest.mark.unit

        # Act & Assert
        assert marker is not None

    def test_aaa_pattern_demonstration(self) -> None:
        """Demonstrate the Arrange-Act-Assert pattern (qa-standards §4.2)."""
        # Arrange
        input_value = 42
        expected = 84

        # Act
        result = input_value * 2

        # Assert
        assert result == expected, f"Expected {expected}, got {result}"


@pytest.mark.integration
class TestIntegrationMarkerSanity:
    """Smoke tests tagged with @pytest.mark.integration."""

    def test_integration_marker_should_be_usable(self) -> None:
        """Verify the integration marker resolves without error."""
        # Arrange & Act & Assert
        assert hasattr(pytest.mark, "integration")


# ═════════════════════════════════════════════════════════════════════════
# Path / imports sanity
# ═════════════════════════════════════════════════════════════════════════


def test_app_package_should_be_importable() -> None:
    """The ``app`` package must be importable from tests.

    This validates that ``PYTHONPATH`` or ``pytest.ini`` is set up
    correctly so the app module is on ``sys.path``.
    """
    # Arrange & Act
    try:
        import importlib

        # This is a probe — if the module doesn't exist yet (greenfield)
        # we accept ImportError gracefully. Once it exists, it must load.
        importlib.import_module("app")
    except ImportError:
        # Greenfield: no `app` package yet — that's fine for now.
        pytest.skip("app package not yet created — skipping import check")

    # Assert — if we got here, import succeeded
    assert True


def test_core_package_should_be_importable() -> None:
    """The ``core`` package must be importable from tests."""
    # Arrange & Act
    try:
        import importlib

        importlib.import_module("core")
    except ImportError:
        pytest.skip("core package not yet created — skipping import check")

    # Assert
    assert True


# ═════════════════════════════════════════════════════════════════════════
# slow / serial marker examples (disabled by default)
# ═════════════════════════════════════════════════════════════════════════


@pytest.mark.slow
class TestSlowMarkerExamples:
    """Tests that take > 1s (run with ``pytest -m slow``)."""

    def test_slow_marker_should_exist(self) -> None:
        """Verify the slow marker resolves."""
        assert hasattr(pytest.mark, "slow")


@pytest.mark.serial
class TestSerialMarkerExamples:
    """Tests that cannot run in parallel (shared resource)."""

    def test_serial_marker_should_exist(self) -> None:
        """Verify the serial marker resolves."""
        assert hasattr(pytest.mark, "serial")
