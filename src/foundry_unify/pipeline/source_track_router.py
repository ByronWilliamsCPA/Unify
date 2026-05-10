"""Source track detection — determines document vs audio processing path."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from foundry_unify.core.exceptions import MissingSourceTrackError


class SourceTrack(StrEnum):
    """Valid source tracks for foundry-unify input."""

    DOCUMENT = "document"
    AUDIO = "audio"


class SourceTrackRouter:
    """Validates and extracts the source_track field from raw input metadata.

    Raises MissingSourceTrackError (maps to HTTP 422) for absent or unknown values.
    """

    _VALID: frozenset[str] = frozenset(t.value for t in SourceTrack)

    @classmethod
    def detect(cls, metadata: dict[str, Any]) -> SourceTrack:
        """Return the SourceTrack for the given metadata dict.

        Args:
            metadata: Raw JSON-parsed input metadata (DocumentMetadata or TranscriptMetadata).

        Raises:
            MissingSourceTrackError: If source_track is absent, None, or unrecognized.
        """
        value = metadata.get("source_track")
        if not value or value not in cls._VALID:
            raise MissingSourceTrackError(received=str(value) if value else None)
        return SourceTrack(value)
