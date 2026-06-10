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
    def test_settings_and_logging_integration(self) -> None:
        """Verify Settings and logging work together.

        This test demonstrates that configuration and logging
        can be integrated properly.
        """
        from foundry_unify.core.config import Settings
        from foundry_unify.utils.logging import get_logger

        settings = Settings(log_level="INFO")
        logger = get_logger(__name__)

        assert settings.log_level == "INFO"
        assert logger is not None

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
