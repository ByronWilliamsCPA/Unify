"""LayoutPostprocessor — applies KI-002 Table misclassification mitigation.

KI-002: Multi-column body text is misclassified as Table with 100% false-positive
rate when Docling layout confidence is below ~0.5. This postprocessor reclassifies
Table detections at or below the confidence threshold to Text, preventing downstream
reading-order corruption (KI-008).

Reference: image_detection/docs/known_issues/KI-002-docling-table-multicolumn.md
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass
class LayoutPostprocessor:
    """Applies KI-002 per-class confidence threshold to raw Docling page data.

    Args:
        confidence_threshold: Table detections at or below this value are
            reclassified to Text. Default matches the B1 config setting.
    """

    confidence_threshold: float = 0.5

    def apply(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply KI-002 mitigation to the pages list from a Docling JSON response.

        Args:
            pages: The `pages` list from `json_content` in the Docling response.
                Each page is a dict with `items` (layout elements).

        Returns:
            A deep-copied pages list with low-confidence Table elements reclassified.
        """
        if not pages:
            return []

        result = copy.deepcopy(pages)
        for page in result:
            for item in page.get("items", []):
                if item.get("label") != "Table":
                    continue
                # Missing confidence field defaults to 1.0 — no reclassification
                confidence: float = item.get("confidence", 1.0)
                if confidence <= self.confidence_threshold:
                    item["label"] = "Text"
                    item["ki002_reclassified"] = True
        return result
