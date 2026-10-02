---
description: "Pointer to the canonical Level 0 page showing where Unify sits in the Foundry pipeline."
status: active
---

# Level 0: Foundry Pipeline Context

The canonical Level 0 diagram is [Foundry Pipeline: Level 0 Architecture](../../pipeline-level-0.md). That page is
identical in all five pipeline repositories, so it is not copied here.

In that diagram, this repository is the **Unify** box, stage 3 of five (Ingest, Prepare-Doc or Prepare-Audio, Unify,
Chunk). Unify reads `01-preprocessed/` or `02-transcribed/`, writes `03-docling-dom/`, and hands `DoclingDOM.json`
to Chunk. The pipeline ends at chunks. For the inside of the Unify box, see the
[Level 1 architecture](../level-1/index.md).
