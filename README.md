# AITF Procurement Screening Backend

Sistem screening dokumen pengadaan pemerintah Indonesia (TOR/RAB) dalam dua tahap: Format dan Substansi.

## Arsitektur

```mermaid
flowchart LR
  Client --> API[FastAPI]
  API --> DB[(PostgreSQL)]
  API --> QD[(Qdrant)]
  API --> EMBED[Embedding Model]
  API --> LLM[LLM Service]
  EMBED --> QD
  LLM --> QD
```

## ERD

```mermaid
erDiagram
  PROJECTS ||--o{ DOCUMENTS : has
  DOCUMENTS ||--o{ CHUNKS : contains
  PROJECTS ||--o{ SCREENING_SESSIONS : runs
  SCREENING_SESSIONS ||--o{ FORMAT_CHECK_RESULTS : checks
  SCREENING_SESSIONS ||--o{ SCREENING_RESULTS : records
  SCREENING_SESSIONS ||--o{ LLM_OUTPUTS : produces
  CHECKLIST_ITEMS ||--o{ FORMAT_CHECK_RESULTS : defines
  CHECKLIST_ITEMS ||--o{ LLM_OUTPUTS : guides
  
  PROJECTS {
    uuid id PK
    varchar name
    varchar client_name
    varchar description
    enum status
  }
  
  DOCUMENTS {
    uuid id PK
    uuid project_id FK
    enum doc_type
    varchar file_name
    varchar file_path
    text extracted_text
    enum status
  }
  
  CHUNKS {
    uuid id PK
    uuid document_id FK
    text content
    int chunk_index
    enum chunk_type
    varchar pasal_number
    int page_number
    varchar qdrant_point_id
    varchar collection_name
  }
  
  CHECKLIST_ITEMS {
    uuid id PK
    int checklist_number
    varchar item_key
    varchar description
    varchar category
  }
  
  SCREENING_SESSIONS {
    uuid id PK
    uuid project_id FK
    int screening_number
    enum status
    datetime started_at
    datetime completed_at
    enum final_result
  }
  
  FORMAT_CHECK_RESULTS {
    uuid id PK
    uuid session_id FK
    uuid document_id FK
    uuid checklist_item_id FK
    bool passed
    text notes
  }
  
  SCREENING_RESULTS {
    uuid id PK
    uuid session_id FK
    uuid document_id FK
    enum stage
    bool passed
    text summary
  }
  
  LLM_OUTPUTS {
    uuid id PK
    uuid session_id FK
    uuid document_id FK
    uuid checklist_item_id FK
    enum classification
    text recommendation
    text reason
    json evidence_json
  }
```

## Setup

### Local
1. `pip install -r requirements.txt`
2. `alembic upgrade head`
3. `uvicorn app.main:app --reload`

### Docker
1. `cp .env.example .env` → isi variabel
2. `docker compose up -d`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://aitf:aitf_secret@localhost:5432/aitf_db` | PostgreSQL connection |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `LLM_API_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_API_KEY` | — | API key for LLM |
| `UPLOAD_DIR` | `./uploads` | Upload directory path |
| `MAX_UPLOAD_SIZE_MB` | `25` | Max file size in MB |

## API Endpoints

### Health Check
- `GET /health` → `{"status":"ok","postgres":"ok","qdrant":"ok"}`

### Projects
- `POST /api/v1/projects` → `{"name":"Pekerjaan X","client_name":"Kemenkeu"}`
- `GET /api/v1/projects` → `[...]`
- `GET /api/v1/projects/{id}` → `{"id":"...","name":"...","screening_status":[...]}`
- `GET /api/v1/projects/{id}/results` → full report

### Documents
- `POST /api/v1/documents/upload` (multipart) → `project_id`, `doc_type`, `file`
- `GET /api/v1/documents/{id}` → `{"id":"...","file_name":"tor.pdf",...}`
- `DELETE /api/v1/documents/{id}` → 204

### Screening
- `POST /api/v1/screening/1/start` → `{"project_id":"..."}`
- `GET /api/v1/screening/1/{session_id}` → format check details
- `POST /api/v1/screening/2/start` → `{"project_id":"..."}` (only if S1 LOLOS)
- `GET /api/v1/screening/2/{session_id}` → LLM outputs
- `POST /api/v1/screening/{session_id}/approve` → ROCAN approval
- `POST /api/v1/screening/{session_id}/reject` → ROCAN rejection

## Screening Pipeline

1. **Screening 1 (Format)**
   - Seed checklist rules
   - Match regex patterns on extracted text
   - Final result: `LOLOS` (all pass), `REVISI` (some fail)

2. **Screening 2 (Substance)**
   - Chunk TOR → embed → upsert to `tor_chunks`
   - Query `tor_chunks` + `reference_chunks` per checklist item
   - LLM evaluates compliance → `LOLOS/TIDAK_LOLOS/PERLU_REVISI`

## Qdrant Collections

- `tor_chunks`: temporary, per-project chunks (768-dim vectors)
- `reference_chunks`: permanent regulatory docs (768-dim vectors)

Payload schema:
```json
{
  "document_id": "uuid",
  "project_id": "uuid",
  "chunk_index": 0,
  "source_type": "TOR",
  "collection_name": "tor_chunks",
  "pasal_number": "Pasal 5",
  "page_number": 3,
  "content": "..."
}
```

## License
MIT
# backend_team2
