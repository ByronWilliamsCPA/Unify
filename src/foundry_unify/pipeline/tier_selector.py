"""Tier selection — maps DocumentMetadata processing recommendation to a pipeline tier."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from foundry_unify.models.document_metadata import InboundDocumentMetadata


class ProcessingTier(StrEnum):
    """Docling pipeline tier for a given document."""

    STANDARD = "standard"
    VLM_ASSISTED = "vlm_assisted"
    VLM_VALIDATED = "vlm_validated"
    HALTED = "halted"


class TierSelector:
    """Reads processing_recommendation.tier from DocumentMetadata and returns the tier.

    Halted documents (encrypted, unreadable) bypass OCR entirely and emit a
    DoclingDOM with processing_status: "halted".
    """

    @staticmethod
    def select(metadata: InboundDocumentMetadata) -> ProcessingTier:
        """Return the ProcessingTier for this document.

        Args:
            metadata: Parsed inbound DocumentMetadata.

        Returns:
            HALTED if processing_status is "halted"; otherwise the tier from
            processing_recommendation (defaults to STANDARD).
        """
        if metadata.processing_status == "halted":
            return ProcessingTier.HALTED

        if metadata.processing_recommendation:
            return ProcessingTier(metadata.processing_recommendation.tier)

        return ProcessingTier.STANDARD
