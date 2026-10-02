# Backend AITF — Ringkasan dan Flow

> **Catatan status:** bagian awal dokumen ini menjelaskan prototype yang tersedia saat ini. Bagian **Pipeline Target yang Disepakati** menjelaskan desain berikutnya dan belum diimplementasikan.

## Pipeline Target yang Disepakati

Desain lengkap: [`docs/superpowers/specs/2026-10-02-ingestion-foundation-design.md`](docs/superpowers/specs/2026-10-02-ingestion-foundation-design.md).

```text
JSON Extractor ──────────┐
                        ├── Canonical Ingestion Service
Upload → JSON Adapter ───┘
             │
             ▼
Validasi + idempotensi + document versioning
             │
             ▼
PostgreSQL + durable ingestion job → 202 Accepted
             │
             ▼
DB-backed worker
      ┌──────┴─────────────┐
      ▼                    ▼
RAB relational         TOR narrative
Rule engine            Chunk + E5 embedding
Regulation version     VectorDB HTTP API
      │                    │
      └──────────┬─────────┘
                 ▼
        Screening 1 dan 2
                 ▼
          Human/ROCAN review
```

Keputusan arsitektur:

- `POST /api/v1/ingestions` menjadi endpoint canonical.
- Upload file hanya adapter menuju contract JSON yang sama.
- PostgreSQL menjadi source of truth; VectorDB adalah indeks turunan.
- RAB disimpan per row dan diperiksa secara deterministik.
- TOR disimpan per versi/page/chunk sebelum dikirim ke VectorDB.
- Worker memakai job PostgreSQL dengan lease, heartbeat, retry, dan recovery.
- Backend membuat embedding `intfloat/multilingual-e5-base` 768 dimensi.
- Backend memanggil API tim VectorDB; akses Qdrant langsung dihentikan dari business flow.
- Regulasi berbeda tiap tahun memakai versioned rows, bukan tabel tahunan.
- LLM memberi rekomendasi; keputusan akhir tetap milik manusia.

Lifecycle target:

```text
ACCEPTED → VALIDATING → NORMALIZING → STORED
  ├── RAB/SBM → RULE_EVALUATION → COMPLETED
  └── TOR/ACUAN/KEPMEN → CHUNKING → EMBEDDING
      → READY_FOR_VECTOR_DB → INDEXING
      → INDEXED | PARTIALLY_INDEXED
```

---

## 1. Tujuan Sistem

Backend AITF membantu memeriksa dokumen pengadaan, terutama **TOR** dan **RAB**, melalui dua tahap:

1. **Screening 1 — Pemeriksaan format**  
   Rule engine memastikan bagian wajib tersedia, misalnya latar belakang, tujuan, ruang lingkup, jadwal, harga satuan, dan total biaya.
2. **Screening 2 — Pemeriksaan substansi**  
   Sistem mencari bagian dokumen yang relevan menggunakan embedding dan Qdrant, lalu LLM memberikan klasifikasi, alasan, rekomendasi, dan bukti.

Keputusan AI bukan keputusan final. Pengguna atau tim **ROCAN** tetap memeriksa bukti lalu menyetujui atau menolak hasil.

---

## 2. Arsitektur

```mermaid
flowchart LR
    U[User / Frontend] --> API[FastAPI]
    API --> PG[(PostgreSQL)]
    API --> EX[Document Extractor]
    EX --> CH[Chunking]
    CH --> EM[Embedding Model]
    EM --> QD[(Qdrant)]
    API --> RE[Rule Engine]
    QD --> RAG[RAG Pipeline]
    RAG --> LLM[LLM / Qwen-compatible API]
    LLM --> PG
    RE --> PG
    PG --> API
```

### Fungsi komponen

| Komponen | Fungsi |
|---|---|
| FastAPI | Menyediakan REST API untuk project, dokumen, dan screening |
| PostgreSQL | Sumber data utama: metadata, teks, checklist, status, dan hasil |
| Qdrant | Menyimpan embedding chunk untuk pencarian semantik |
| Document Extractor | Mengambil teks dari PDF, DOCX, atau TXT |
| Rule Engine | Memeriksa kelengkapan format TOR dan RAB |
| Embedding Model | Mengubah teks menjadi vector 768 dimensi |
| RAG Pipeline | Mengambil potongan TOR dan dokumen acuan yang relevan |
| LLM | Menghasilkan klasifikasi, alasan, rekomendasi, dan bukti |

---

## 3. Flow Utama

```mermaid
flowchart TD
    A[Buat Project] --> B[Upload TOR dan RAB]
    B --> C[Ekstraksi Teks]
    C --> D{Ekstraksi berhasil?}
    D -- Tidak --> E[Status Dokumen ERROR]
    D -- Ya --> F[Status Dokumen PROCESSED]
    F --> G[Mulai Screening 1]
    G --> H[Rule Engine memeriksa format]
    H --> I{Semua aturan lolos?}
    I -- Tidak --> J[Hasil REVISI]
    J --> B
    I -- Ya --> K[Hasil LOLOS]
    K --> L[Mulai Screening 2]
    L --> M[Chunking dan Embedding]
    M --> N[Simpan dan cari vector di Qdrant]
    N --> O[LLM mengevaluasi substansi]
    O --> P[LOLOS / TIDAK_LOLOS / PERLU_REVISI]
    P --> Q[Manusia memeriksa alasan dan bukti]
    Q --> R{Keputusan ROCAN}
    R -- Setuju --> S[Approve]
    R -- Tidak --> T[Reject / revisi dokumen]
```

### Screening 1

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant DB as PostgreSQL
    participant RE as Rule Engine

    U->>API: POST /screening/1/start
    API->>DB: Ambil TOR dan RAB PROCESSED
    API->>RE: Jalankan aturan format
    RE-->>API: Hasil per checklist
    API->>DB: Simpan detail dan hasil akhir
    API-->>U: LOLOS atau REVISI
```

### Screening 2

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Q as Qdrant
    participant L as LLM

    U->>API: POST /screening/2/start
    API->>DB: Pastikan Screening 1 LOLOS
    API-->>U: Session dibuat
    API->>DB: Ambil teks TOR dan checklist
    API->>Q: Upsert embedding chunk
    API->>Q: Cari Top-K TOR dan acuan
    Q-->>API: Passage relevan
    API->>L: Kriteria + passage + prompt
    L-->>API: Klasifikasi + alasan + bukti
    API->>DB: Simpan output LLM
```

---

## 4. ERD Ringkas

```mermaid
erDiagram
    PROJECTS ||--o{ DOCUMENTS : memiliki
    PROJECTS ||--o{ SCREENING_SESSIONS : menjalankan
    DOCUMENTS ||--o{ CHUNKS : dipecah_menjadi
    DOCUMENTS ||--o{ FORMAT_CHECK_RESULTS : diperiksa
    DOCUMENTS ||--o{ SCREENING_RESULTS : menghasilkan
    DOCUMENTS ||--o{ LLM_OUTPUTS : dianalisis
    SCREENING_SESSIONS ||--o{ FORMAT_CHECK_RESULTS : berisi
    SCREENING_SESSIONS ||--o{ SCREENING_RESULTS : merangkum
    SCREENING_SESSIONS ||--o{ LLM_OUTPUTS : menghasilkan
    CHECKLIST_ITEMS ||--o{ FORMAT_CHECK_RESULTS : menjadi_acuan
    CHECKLIST_ITEMS ||--o{ LLM_OUTPUTS : menjadi_kriteria
```

| Tabel | Isi utama |
|---|---|
| `projects` | Data pekerjaan dan klien |
| `documents` | File TOR, RAB, acuan, teks hasil ekstraksi, dan status |
| `chunks` | Potongan dokumen serta ID point Qdrant |
| `checklist_items` | Kriteria pemeriksaan format dan substansi |
| `screening_sessions` | Satu pelaksanaan Screening 1 atau 2 |
| `format_check_results` | Hasil rule engine per checklist |
| `screening_results` | Ringkasan hasil per tahap dan dokumen |
| `llm_outputs` | Klasifikasi, alasan, rekomendasi, dan bukti dari LLM |

PostgreSQL adalah **source of truth**. Qdrant hanya digunakan untuk pencarian vector.

---

## 5. Data Qdrant

Collection yang digunakan:

- `tor_chunks_<project>`: chunk TOR milik satu project.
- `reference_chunks`: chunk dokumen acuan yang dapat digunakan kembali.

Contoh point:

```json
{
  "id": "29587e23-a58a-45b4-954b-10af450a3991",
  "vector": [0.014, -0.028, 0.091],
  "payload": {
    "document_id": "2d80aaac-86db-45e5-b894-8a46ccb45596",
    "project_id": "fb3cf880-e53d-4fe6-a66c-e572b5b85db0",
    "chunk_index": 3,
    "source_type": "TOR",
    "collection_name": "tor_chunks_fb3cf880",
    "pasal_number": null,
    "page_number": 4,
    "content": "Ruang lingkup kegiatan ini meliputi..."
  }
}
```

Vector asli berisi 768 angka; contoh dipersingkat.

---

## 6. API Utama

Base URL lokal:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/health` | Memeriksa API, PostgreSQL, dan Qdrant |
| `POST` | `/api/v1/projects` | Membuat project |
| `GET` | `/api/v1/projects` | Menampilkan daftar project |
| `GET` | `/api/v1/projects/{id}` | Menampilkan detail project |
| `PATCH` | `/api/v1/projects/{id}` | Memperbarui project |
| `DELETE` | `/api/v1/projects/{id}` | Menghapus project |
| `GET` | `/api/v1/projects/{id}/results` | Mengambil ringkasan hasil |
| `POST` | `/api/v1/documents/upload` | Mengunggah dokumen |
| `GET` | `/api/v1/documents/{id}` | Melihat status dokumen |
| `DELETE` | `/api/v1/documents/{id}` | Menghapus dokumen dan vector terkait |
| `POST` | `/api/v1/screening/1/start` | Menjalankan pemeriksaan format |
| `GET` | `/api/v1/screening/1/{session_id}` | Mengambil hasil Screening 1 |
| `POST` | `/api/v1/screening/2/start` | Menjalankan pemeriksaan substansi |
| `GET` | `/api/v1/screening/2/{session_id}` | Mengambil hasil Screening 2 |
| `POST` | `/api/v1/screening/{session_id}/approve` | Menyetujui hasil |
| `POST` | `/api/v1/screening/{session_id}/reject` | Menolak hasil |

### Contoh membuat project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Evaluasi Pengadaan 2026",
    "client_name": "Instansi Contoh",
    "description": "Pemeriksaan TOR dan RAB"
  }'
```

### Contoh upload TOR

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "project_id=UUID_PROJECT" \
  -F "doc_type=TOR" \
  -F "file=@TOR.pdf"
```

Format file yang diterima: PDF, DOCX, dan TXT. Batas default: 25 MB.

### Memulai Screening 1

```bash
curl -X POST http://localhost:8000/api/v1/screening/1/start \
  -H "Content-Type: application/json" \
  -d '{"project_id":"UUID_PROJECT"}'
```

### Memulai Screening 2

```bash
curl -X POST http://localhost:8000/api/v1/screening/2/start \
  -H "Content-Type: application/json" \
  -d '{"project_id":"UUID_PROJECT"}'
```

Screening 2 ditolak jika Screening 1 terbaru belum `LOLOS`.

---

## 7. Human-in-the-Loop

Bagian otomatis:

- Ekstraksi teks.
- Pemeriksaan format berbasis aturan.
- Chunking dan embedding.
- Pencarian passage relevan.
- Rekomendasi awal dari LLM.

Bagian yang wajib diperiksa manusia:

- Apakah hasil ekstraksi sesuai dokumen asli.
- Apakah rule engine memberi hasil yang masuk akal.
- Apakah kutipan bukti benar-benar mendukung alasan LLM.
- Apakah rekomendasi sesuai aturan pengadaan yang berlaku.
- Keputusan approve atau reject.

LLM dapat salah atau menghasilkan bukti yang kurang tepat. Dokumen asli tetap menjadi rujukan final.

---

## 8. Cara Menjalankan

```bash
cd ~/Downloads/AITF/backend
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Lalu buka:

```text
http://localhost:8000/docs
```

Konfigurasi utama di `.env`:

```env
DATABASE_URL=postgresql+asyncpg://aitf:aitf_secret@postgres:5432/aitf_db
QDRANT_URL=http://qdrant:6333
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=isi_api_key
LLM_MODEL=Qwen/Qwen3-8B
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2
MAX_UPLOAD_SIZE_MB=25
```

---

## 9. Checklist Manual Sederhana

- [ ] `docker compose up -d --build` berhasil.
- [ ] `alembic upgrade head` berhasil.
- [ ] `GET /health` dapat diakses.
- [ ] Project dapat dibuat.
- [ ] TOR dan RAB dapat diunggah.
- [ ] Status dokumen berubah menjadi `PROCESSED`.
- [ ] Screening 1 menghasilkan detail checklist.
- [ ] Screening 2 ditolak jika Screening 1 belum `LOLOS`.
- [ ] Screening 2 dapat berjalan setelah Screening 1 `LOLOS`.
- [ ] Alasan dan evidence dibandingkan dengan dokumen asli.
- [ ] ROCAN dapat approve atau reject hasil.
- [ ] File tidak valid dan file di atas 25 MB ditolak.

---

## 10. Status dan Batasan

- Struktur backend dan endpoint sudah diimplementasikan.
- Pemeriksaan kompilasi Python sudah lulus.
- Runtime penuh dengan PostgreSQL, Qdrant, embedding, dan LLM belum diverifikasi end-to-end.
- Belum ada autentikasi atau pembagian role.
- Dokumen PDF hasil scan memerlukan OCR; extractor saat ini berfokus pada PDF bertulisan digital.
- Model embedding pertama kali akan diunduh dan membutuhkan koneksi internet serta ruang penyimpanan.
- API key LLM diperlukan untuk Screening 2.
- Dokumen pengadaan dapat bersifat sensitif; jangan gunakan konfigurasi default untuk production.
