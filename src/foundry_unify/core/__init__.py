"""Core configuration, settings, and exception modules."""

from foundry_unify.core.config import Settings
from foundry_unify.core.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConfigurationError,
    DatabaseError,
    DoclingServiceError,
    ExternalServiceError,
    GCSError,
    MissingDoclingDOMError,
    MissingSourceTrackError,
    ProjectBaseError,
    ResourceNotFoundError,
    ValidationError,
)

__all__ = [
    # Exceptions (sorted alphabetically)
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ConfigurationError",
    "DatabaseError",
    "DoclingServiceError",
    "ExternalServiceError",
    "GCSError",
    "MissingDoclingDOMError",
    "MissingSourceTrackError",
    "ProjectBaseError",
    "ResourceNotFoundError",
    # Configuration
    "Settings",
    "ValidationError",
]
