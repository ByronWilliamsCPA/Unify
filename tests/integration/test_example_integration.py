"""Integration tests demonstrating end-to-end workflows.

These tests verify that multiple components work together to accomplish
realistic tasks. They live under tests/integration/ so that workflows
using path-based exclusion (e.g. python-compatibility) skip them.
"""

from __future__ import annotations

import pytest


class TestExampleIntegration:
    """Integration tests demonstrating end-to-end workflows."""

    @pytest.mark.integration
    def test_settings_and_logging_integration(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify Settings-driven log configuration reaches the log output.

        Configures logging from a Settings value and asserts that a record
        emitted at that level actually flows through the stdlib logging
        pipeline structlog is bound to, proving the two components integrate
        rather than merely coexist.
        """
        import logging

        from foundry_unify.core.config import Settings
        from foundry_unify.utils.logging import get_logger, setup_logging

        settings = Settings(log_level="DEBUG")
        setup_logging(level=settings.log_level, json_logs=True)
        logger = get_logger(__name__)

        with caplog.at_level(logging.DEBUG):
            logger.debug("settings-logging-integration-probe")

        assert any(
            "settings-logging-integration-probe" in record.getMessage()
            for record in caplog.records
        )

    @pytest.mark.integration
    def test_package_imports(self) -> None:
        """Verify all public API imports work correctly.

        This test ensures that users can import the public API
        from the package root without errors.
        """
        # Test importing main package
        import foundry_unify

        assert hasattr(foundry_unify, "__version__")

        # Test importing from submodules
        from foundry_unify.utils import get_logger

        assert callable(get_logger)

        from foundry_unify.core import Settings

        assert Settings is not None
