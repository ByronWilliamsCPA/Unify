"""GCS adapter -- reads DocumentMetadata.json from 01-preprocessed/ and writes DoclingDOM.json.

Paths follow the canonical GCS layout:
  gs://rag-pipeline-{env}/{trace_id}/01-preprocessed/DocumentMetadata.json  (read)
  gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json          (write)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from foundry_unify.core.exceptions import GCSError

if TYPE_CHECKING:
    from foundry_unify.models.docling_dom import DoclingDOM
from foundry_unify.models.document_metadata import InboundDocumentMetadata
from foundry_unify.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GCSArtifactReader:
    """Downloads DocumentMetadata.json from the 01-preprocessed/ GCS path."""

    bucket_template: str = "rag-pipeline-{env}"
    client: Any = field(default=None, repr=False)  # pyright: ignore[reportAny, reportExplicitAny]  # GCS client typed as Any; runtime injection via dataclass field

    def _get_client(self) -> Any:  # pyright: ignore[reportAny, reportExplicitAny]
        if self.client is None:  # pyright: ignore[reportAny]
            from google.cloud import storage

            self.client = storage.Client()
        return self.client  # pyright: ignore[reportAny]

    def download_document_metadata(
        self, env: str, trace_id: str
    ) -> InboundDocumentMetadata:
        """Download and parse DocumentMetadata.json for the given trace.

        Args:
            env: Deployment environment (dev, staging, prod).
            trace_id: Cloud Workflows trace identifier.

        Returns:
            Parsed InboundDocumentMetadata instance.

        Raises:
            GCSError: On any GCS access failure.
        """
        bucket_name = self.bucket_template.format(env=env)
        blob_path = f"{trace_id}/01-preprocessed/DocumentMetadata.json"
        gcs_path = f"gs://{bucket_name}/{blob_path}"

        logger.info("gcs_read_start", path=gcs_path)
        try:
            # #ASSUME: external_resources: GCS bucket and blob exist and are readable
            # #VERIFY: bucket and blob existence; caller should handle GCSError
            text: str = (  # pyright: ignore[reportAny]
                self._get_client()  # pyright: ignore[reportAny]
                .bucket(bucket_name)  # pyright: ignore[reportAny]
                .blob(blob_path)  # pyright: ignore[reportAny]
                .download_as_text()  # pyright: ignore[reportAny]  # GCS SDK has no stubs
            )
        except Exception as exc:  # nosec BLE001 -- GCS SDK raises heterogeneous exceptions (google-api-core, network errors, auth errors); spec requires wrapping all in GCSError
            msg = f"Failed to download DocumentMetadata.json: {exc}"
            raise GCSError(msg, path=gcs_path) from exc

        return InboundDocumentMetadata.model_validate_json(text)


@dataclass
class GCSArtifactWriter:
    """Writes the assembled DoclingDOM.json to the 03-docling-dom/ GCS path."""

    bucket_template: str = "rag-pipeline-{env}"
    client: Any = field(default=None, repr=False)  # pyright: ignore[reportAny, reportExplicitAny]  # GCS client typed as Any; runtime injection via dataclass field

    def _get_client(self) -> Any:  # pyright: ignore[reportAny, reportExplicitAny]
        if self.client is None:  # pyright: ignore[reportAny]
            from google.cloud import storage

            self.client = storage.Client()
        return self.client  # pyright: ignore[reportAny]

    def write_docling_dom(
        self,
        dom: DoclingDOM,
        env: str,
        trace_id: str,
    ) -> str:
        """Serialize DoclingDOM to JSON and upload to GCS.

        Args:
            dom: Assembled DoclingDOM instance.
            env: Deployment environment.
            trace_id: Cloud Workflows trace identifier.

        Returns:
            Full GCS URI of the written artifact.

        Raises:
            GCSError: On upload failure.
        """
        bucket_name = self.bucket_template.format(env=env)
        blob_path = f"{trace_id}/03-docling-dom/DoclingDOM.json"
        gcs_path = f"gs://{bucket_name}/{blob_path}"

        json_bytes = dom.model_dump_json(indent=2).encode("utf-8")

        logger.info("gcs_write_start", path=gcs_path, bytes=len(json_bytes))
        try:
            # #ASSUME: external_resources: GCS bucket exists and is writable
            # #VERIFY: bucket existence and write permissions; caller should handle GCSError
            blob = (  # pyright: ignore[reportAny]
                self._get_client()  # pyright: ignore[reportAny]
                .bucket(bucket_name)  # pyright: ignore[reportAny]
                .blob(blob_path)  # pyright: ignore[reportAny]  # GCS SDK has no stubs
            )
            blob.upload_from_string(  # pyright: ignore[reportAny]  # GCS SDK has no stubs
                data=json_bytes,
                content_type="application/json",
            )
        except Exception as exc:  # nosec BLE001 -- GCS SDK raises heterogeneous exceptions (google-api-core, network errors, quota errors); spec requires wrapping all in GCSError
            msg = f"Failed to write DoclingDOM.json: {exc}"
            raise GCSError(msg, path=gcs_path) from exc

        logger.info("gcs_write_complete", path=gcs_path)
        return gcs_path
