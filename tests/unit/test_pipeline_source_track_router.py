"""Tests for SourceTrackRouter."""

import pytest

from foundry_unify.core.exceptions import MissingSourceTrackError
from foundry_unify.pipeline.source_track_router import SourceTrack, SourceTrackRouter


@pytest.mark.unit
def test_routes_document_track() -> None:
    track = SourceTrackRouter.detect({"source_track": "document"})
    assert track == SourceTrack.DOCUMENT


@pytest.mark.unit
def test_routes_audio_track() -> None:
    track = SourceTrackRouter.detect({"source_track": "audio"})
    assert track == SourceTrack.AUDIO


@pytest.mark.unit
def test_raises_on_missing_source_track() -> None:
    with pytest.raises(MissingSourceTrackError) as exc_info:
        SourceTrackRouter.detect({})
    assert exc_info.value.error_code == "MISSING_SOURCE_TRACK"


@pytest.mark.unit
def test_raises_on_unknown_source_track() -> None:
    with pytest.raises(MissingSourceTrackError) as exc_info:
        SourceTrackRouter.detect({"source_track": "video"})
    assert exc_info.value.details["value"] == "video"


@pytest.mark.unit
def test_raises_on_none_source_track() -> None:
    with pytest.raises(MissingSourceTrackError):
        SourceTrackRouter.detect({"source_track": None})
