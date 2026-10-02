# AITF Backend — Ingestion Foundation Design

**Date:** 2026-10-02  
**Status:** Proposed  
**Scope:** Backend Team 2

## 1. Context

The current prototype accepts uploaded files, extracts text inside FastAPI, stores one text field per document, runs hardcoded format rules, embeds TOR chunks, and accesses Qdrant directly. The target integration contract instead expects JSON from Document Extractor, durable ingestion status, structured RAB data, versioned documents and regulations, and vector delivery through the VectorDB team's API.

This release establishes that foundation without importing official regulatory data or introducing Redis/Celery.

## 2. Goals

- Establish `POST /api/v1/ingestions` as the canonical input flow.
- Keep file upload as an adapter that produces the same internal ingestion command.
- Preserve extractor-issued stable `document_id` values.
- Create a new document version when the checksum changes.
- Make duplicate delivery idempotent.
- Persist RAB rows as relational data for deterministic validation.
- Persist TOR pages and chunks in PostgreSQL; use VectorDB only as a rebuildable index.
- Process ingestion asynchronously through PostgreSQL-backed jobs.
- Generate 768-dimensional embeddings with `intfloat/multilingual-e5-base`.
- Send vector batches to the VectorDB team's HTTP API instead of accessing Qdrant directly.
- Provide versioned regulation/rule schema with clearly labeled non-production seed rules.
- Improve flow documentation, setup instructions, failure descriptions, and verification guidance.

## 3. Non-goals

- Importing or certifying official SBM/PMK datasets.
- Building the Document Extractor service.
- Building the VectorDB service or managing Qdrant collections.
- Production authentication/authorization implementation.
- LLM model redesign.
- Full distributed workflow orchestration.
- Automatic legal interpretation. Deterministic rules remain reviewable and human-approved.

## 4. Ownership and Boundaries

```text
Document Extractor
  owns file parsing/OCR and emits JSON v1.0
        │
        ▼
Backend Team 2
  validates, versions, normalizes, stores, evaluates,
  chunks, embeds, batches, retries, and records acknowledgments
        │
        ▼
VectorDB Team API
  validates vectors, upserts/searches/deactivates points,
  and returns batch acknowledgment
```

PostgreSQL is the business source of truth. Original files live in file/object storage. VectorDB is a derived retrieval index.

## 5. Canonical Input Contract

`POST /api/v1/ingestions` accepts JSON and returns `202 Accepted` after transactionally storing the request, document/version records, source contents, and job.

Required top-level fields:

- `schema_version = "1.0"`
- `request_id`: UUID, unique idempotency key
- `project_id`: existing project UUID
- `document.document_id`: stable UUID created by Extractor
- `document.document_type`: `TOR`, `RAB`, `SBM`, `ACUAN`, or `KEPMEN`
- file metadata and SHA-256 checksum
- `pages` and/or `tables`

The backend stores the validated raw payload in JSON form for audit. Secrets and binary file contents are excluded.

### Idempotency and revisions

| Condition | Result |
|---|---|
| Same `request_id`, same canonical payload hash | Return the existing ingestion response |
| Same `request_id`, different payload hash | `409 IDEMPOTENCY_CONFLICT` |
| Same `document_id`, same checksum | Reuse the existing document version; create no duplicate contents/chunks |
| Same `document_id`, different checksum | Create the next version and mark the prior version inactive |

`document_id` remains stable. `document_version_id` identifies one immutable revision.

## 6. Upload Adapter

`POST /api/v1/documents/upload` remains available but no longer owns a separate processing pipeline.

```text
multipart upload
  → validate extension, MIME, and size
  → store original file
  → extract pages/tables through local prototype extractor
  → construct JSON v1.0 ingestion command
  → call the canonical ingestion service
  → return 202 ingestion response
```

The adapter generates `request_id`, checksum, and a new stable `document_id` because no external Extractor supplied one. Future revisions uploaded through this endpoint must accept an optional existing `document_id`.

## 7. Data Model

Existing project and screening tables remain. A new Alembic revision adds the foundation tables and compatibility links.

### Core document tables

- `documents`: stable identity, project, document type, current version reference.
- `document_versions`: immutable checksum-based revisions, version number, source metadata, storage URI, active status.
- `document_contents`: page-level text/table source, raw metadata, extraction confidence.
- `document_tables`: extracted table identity and normalized columns.
- `rab_items`: normalized RAB rows using `NUMERIC` for quantities and money.
- `document_chunks`: version-scoped chunks with stable deterministic IDs.

### Processing tables

- `ingestion_jobs`: state, attempts, next retry, lease owner/expiry, heartbeat, stage, and sanitized error.
- `embedding_records`: chunk, model, dimension, content hash, and status.
- `vector_batches`: collection, model contract, status, counts, request/response metadata.
- `vector_batch_items`: batch-to-chunk/point mapping and per-point result.

### Regulation and rule tables

- `regulations`: stable regulation identity.
- `regulation_versions`: fiscal year, effective period, checksum, source URI, status, superseded version.
- `cost_standards`: normalized category, region, unit, amount/ceiling, currency.
- `validation_rules`: versioned deterministic operator/expression, severity, document type, and source reference.
- `rule_evaluations`: applied rule/version, source RAB row, actual/expected values, result, difference, and evidence.

### Constraints

- Unique `(document_id, checksum_sha256)` document version.
- Unique `(document_id, version_number)`.
- Unique `(document_version_id, page_number, content_type, content_index)`.
- Unique `(document_version_id, chunk_index)`.
- Unique `(chunk_id, embedding_model, content_hash)`.
- Unique `(session_id, rab_item_id, validation_rule_id)` rule evaluation.
- Positive page/table/row/chunk indexes where applicable.
- Currency amounts use `NUMERIC`, never floating-point.
- Foreign keys preserve project/document/version lineage.

Year differences are represented by rows in `regulation_versions`, not yearly tables. Every rule evaluation records the exact regulation and rule version used.

## 8. Ingestion Lifecycle

```text
ACCEPTED
→ VALIDATING
→ NORMALIZING
→ STORED
→ RULE_EVALUATION       (RAB/SBM)
→ CHUNKING              (TOR/ACUAN/KEPMEN)
→ EMBEDDING
→ READY_FOR_VECTOR_DB
→ INDEXING
→ INDEXED | PARTIALLY_INDEXED

Any stage → RETRY_WAIT → prior failed stage
Any exhausted stage → FAILED
```

RAB may complete after `RULE_EVALUATION` without vectorization. TOR proceeds through chunking and indexing. Reference documents use the same narrative pipeline but target `reference_chunks`.

## 9. PostgreSQL-backed Worker

A separate worker process polls eligible jobs. It claims work using a short transaction and `SELECT ... FOR UPDATE SKIP LOCKED`.

Each claim records:

- `lease_owner`
- `lease_expires_at`
- `heartbeat_at`
- incremented `attempt_count`

Long work runs outside the claim transaction. The worker periodically renews the lease. Completion writes output and advances state transactionally. Expired leases become eligible for recovery. Retry delay uses bounded exponential backoff. Permanent validation errors fail immediately; network and dependency errors retry.

Default policy:

- maximum attempts: 5
- lease: 5 minutes, configurable
- poll interval: 2 seconds, configurable
- sanitized error persisted; full stack trace written to structured logs

Only one active job per document version and job type is allowed.

## 10. Document-type Processing

### TOR

1. Store immutable pages/sections.
2. Chunk by section/paragraph with page lineage.
3. Prefix chunk text with `passage:`.
4. Generate normalized 768-dimensional E5 vectors.
5. Build deterministic point IDs from chunk identity and embedding contract.
6. Send a vector batch through VectorDB HTTP API.
7. Persist acknowledgment and per-point status.

### RAB

1. Validate table shape.
2. Preserve raw cells/source text.
3. Normalize description, volume, unit, unit price, total, and currency.
4. Calculate total using decimal arithmetic.
5. Run arithmetic, required-field, non-negative, and example ceiling rules.
6. Persist actual value, expected value, difference, evidence, rule version, and result.

### SBM/ACUAN/KEPMEN

The schema supports structured regulation/version data and reference chunks. This release seeds only clearly marked demonstration records. No seed is represented as an official or production-valid regulatory source.

## 11. Embedding Contract

Default model: `intfloat/multilingual-e5-base`.

- Dimension: 768
- Retrieval input: `query: ...`
- Indexed input: `passage: ...`
- Normalization: enabled
- Distance: cosine

Model, dimension, prefix strategy, normalization, and content hash are persisted. Changing any of them requires a new embedding record and vector reindex; it must not silently mix incompatible vectors.

Final production selection remains subject to an Indonesian procurement-domain benchmark measuring Recall@5, MRR@10, latency, memory, and behavior on numbers/acronyms.

## 12. VectorDB Integration

The backend uses an HTTP adapter configured through `VECTOR_DB_API_URL`, timeout, and optional service credential. Direct `qdrant-client` use is removed from business flow.

Operations:

- upsert vector batch;
- search with mandatory filters;
- deactivate prior document version;
- delete document points when explicitly requested;
- health/readiness check.

TOR search always includes `project_id`, `document_id` when known, and `is_active: true`. Reference search includes active/version filters and follows the configured cross-project policy.

Transient failures retry through the job state. `batch_id` and point IDs remain stable across retries. An acknowledgment updates `vector_batches`, `vector_batch_items`, and the ingestion state.

## 13. Screening Compatibility

Screening 1 reads normalized current document versions. Format checks remain available while rules migrate from hardcoded definitions to versioned records.

Screening 2 requires the latest Screening 1 result to be `LOLOS`. Retrieval calls the VectorDB search API and applies tenant/document filters. LLM output remains advisory and requires ROCAN review.

The release must not silently evaluate inactive revisions.

## 14. Error Contract

Errors use a stable envelope:

```json
{
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "request_id telah digunakan untuk payload berbeda",
    "details": {},
    "request_id": "UUID"
  }
}
```

Minimum codes:

- `INVALID_INGESTION_PAYLOAD`
- `IDEMPOTENCY_CONFLICT`
- `PROJECT_NOT_FOUND`
- `DOCUMENT_VERSION_CONFLICT`
- `RAB_NORMALIZATION_FAILED`
- `EMBEDDING_FAILED`
- `VECTOR_DB_UNAVAILABLE`
- `VECTOR_BATCH_REJECTED`
- `JOB_LEASE_LOST`

API errors avoid internal paths, stack traces, credentials, and raw sensitive document content.

## 15. Security and Privacy

- Validate project ownership boundary before all document, screening, and vector operations.
- Require mandatory project filters in retrieval adapters.
- Keep credentials in environment variables; never persist them.
- Do not return local storage paths or full extracted text in default document responses.
- Validate MIME and extension; stream uploads with bounded size.
- Store raw LLM prompts/responses only behind an explicit retention setting.
- Keep prototype CORS configurable; documentation must warn against wildcard production use.
- Service-to-service authentication remains a documented production blocker, not silently treated as complete.

## 16. Observability

Structured logs include request ID, ingestion ID, job ID, project ID, document ID, version ID, stage, attempt, duration, and dependency status. Document content and credentials are excluded.

Expose:

- `/health`: liveness of API process;
- `/ready`: PostgreSQL and required dependency readiness, returning non-2xx when unavailable;
- job counts by status/stage;
- processing duration and retry count;
- vector batch success/failure counts.

## 17. Deployment

Docker Compose runs separate `api` and `worker` services from the same image. PostgreSQL remains local for development. VectorDB is represented only by an external API URL.

Startup sequence:

1. PostgreSQL becomes healthy.
2. Alembic migration runs explicitly.
3. API and worker start.
4. Readiness confirms dependencies.

The production command excludes Uvicorn `--reload`. Upload/object storage requires a persistent volume or external implementation.

## 18. Migration and Compatibility

- Add a new Alembic revision; do not rewrite `001_initial`.
- Preserve existing project/document/screening data.
- Backfill one active `document_version` for existing documents where possible.
- Existing `chunks` remain readable during transition; new ingestion writes canonical `document_chunks`.
- Mark direct-Qdrant prototype code deprecated, then remove it from active routes/services.
- Upload response changes to an ingestion acknowledgment; README highlights this API change.

## 19. Verification

Automated tests cover:

- JSON schema validation;
- idempotent duplicate request;
- idempotency conflict;
- automatic document revision;
- prior-version deactivation request;
- RAB normalization using decimal values;
- arithmetic and demonstration ceiling rules;
- worker claim, lease expiry, retry, and exhausted failure;
- deterministic chunk and point IDs;
- E5 query/passage prefixing and dimension validation;
- vector batch acknowledgment and partial failure;
- mandatory project filters;
- upload adapter entering the canonical ingestion service;
- migration upgrade on clean PostgreSQL.

Integration verification uses fake embedding and VectorDB adapters by default. A manual profile exercises the real embedding model and external VectorDB sandbox.

## 20. Documentation Deliverables

- Rewrite `README.md` around actual scope, quick start, API, statuses, and current limitations.
- Update `BACKEND_FLOW.md` with canonical JSON/upload flows and RAB/TOR branches.
- Update `TEAM_INTEGRATION_CONTRACT.md` to match implemented fields and explicitly mark future endpoints.
- Update `.env.example`, Docker configuration, and migration/worker commands.
- Include sample TOR and RAB requests plus expected status polling.

## 21. Acceptance Criteria

The release is accepted when:

1. JSON ingestion and upload adapter both create the same canonical records.
2. Duplicate delivery creates no duplicate version, content, chunk, or vector point.
3. Changed checksum creates a new active revision and schedules old-vector deactivation.
4. RAB rows and deterministic evaluation evidence are queryable from PostgreSQL.
5. TOR chunks are embedded with E5 and sent only through the VectorDB API adapter.
6. Jobs recover from process restart through lease expiry.
7. Project filters are mandatory in vector retrieval.
8. Migration, unit tests, static compilation, and Docker configuration checks pass.
9. README and flow documents accurately separate implemented behavior, demonstration data, and future production requirements.
