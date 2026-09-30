"""
RAG Pipeline — Screening 2: Substance check.
Flow: chunks → embed → upsert Qdrant → query per checklist item → LLM → save output
"""
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Document, Chunk, ChecklistItem, ScreeningSession, LLMOutput, ScreeningResult
from app.core.constants import (
    DocType, DocStatus, ScreeningStatus, FinalResult,
    LLMClassification, ScreeningStage, COLLECTION_TOR, COLLECTION_REFERENCE
)
from app.services.chunking import chunk_document
from app.services.embedding import embed_texts, embed_single
from app.services.query_generator import generate_query
from app.services.llm_service import call_llm
from app import qdrant_client as qc


async def run_screening_2(session_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession) -> None:
    """Full Screening 2 pipeline. Called as background task."""

    # Mark session as RUNNING
    sess_q = await db.execute(select(ScreeningSession).where(ScreeningSession.id == session_id))
    screening = sess_q.scalar_one_or_none()
    if not screening:
        return

    screening.status = ScreeningStatus.RUNNING
    screening.started_at = datetime.utcnow()
    await db.commit()

    try:
        # 1. Get TOR documents for this project
        doc_q = await db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.doc_type == DocType.TOR,
                Document.status == DocStatus.PROCESSED,
            )
        )
        tor_docs = doc_q.scalars().all()

        if not tor_docs:
            raise ValueError("Tidak ada dokumen TOR yang sudah diproses untuk project ini")

        # 2. Chunk + embed + upsert TOR docs into Qdrant
        collection_name = COLLECTION_TOR
        qc.ensure_collection(collection_name)

        for doc in tor_docs:
            await _chunk_and_index_document(doc, collection_name, db)

        # 3. Get active checklist items for SUBSTANSI
        items_q = await db.execute(
            select(ChecklistItem).where(
                ChecklistItem.is_active == True,
                ChecklistItem.category == "SUBSTANSI",
            )
        )
        checklist_items = items_q.scalars().all()

        # 4. For each checklist item: query → LLM → save output
        all_passed = True
        for item in checklist_items:
            query_text = generate_query(item.item_key, item.description)
            query_vec = await embed_single(query_text)

            # Search TOR chunks
            tor_hits = qc.search_points(collection_name, query_vec, limit=5)

            # Search reference chunks (permanent collection)
            try:
                ref_hits = qc.search_points(COLLECTION_REFERENCE, query_vec, limit=3)
            except Exception:
                ref_hits = []

            # Call LLM
            llm_result = await call_llm(
                checklist_description=item.description,
                tor_passages=tor_hits,
                reference_passages=ref_hits,
                checklist_item_key=item.item_key,
            )

            # Save LLM output
            classification = LLMClassification(llm_result["classification"])
            if classification != LLMClassification.LOLOS:
                all_passed = False

            output = LLMOutput(
                session_id=session_id,
                document_id=tor_docs[0].id,
                checklist_item_id=item.id,
                classification=classification,
                recommendation=llm_result["recommendation"],
                reason=llm_result["reason"],
                evidence_json=llm_result["evidence"],
                raw_prompt=llm_result.get("raw_prompt"),
                raw_response=llm_result.get("raw_response"),
            )
            db.add(output)

        # 5. Save screening result
        result = ScreeningResult(
            session_id=session_id,
            document_id=tor_docs[0].id,
            stage=ScreeningStage.SUBSTANSI,
            passed=all_passed,
            summary="Semua kriteria substansi LOLOS" if all_passed else "Ada kriteria substansi yang TIDAK LOLOS",
        )
        db.add(result)

        # 6. Update session status
        screening.status = ScreeningStatus.COMPLETED
        screening.completed_at = datetime.utcnow()
        screening.final_result = FinalResult.LOLOS if all_passed else FinalResult.TIDAK_LOLOS
        await db.commit()

    except Exception:
        screening.status = ScreeningStatus.FAILED
        screening.completed_at = datetime.utcnow()
        await db.commit()


async def _chunk_and_index_document(
    doc: Document,
    collection_name: str,
    db: AsyncSession,
) -> None:
    """Chunk document, embed, upsert to Qdrant, save chunk records."""
    if not doc.extracted_text:
        return

    existing = await db.execute(select(Chunk).where(Chunk.document_id == doc.id, Chunk.collection_name == collection_name))
    if existing.scalar_one_or_none() is not None:
        return
    raw_chunks = chunk_document(doc.extracted_text, doc.doc_type)
    if not raw_chunks:
        return

    # Embed all chunks in batch
    texts = [c["content"] for c in raw_chunks]
    vectors = await embed_texts(texts)

    points = []
    chunk_records = []

    for chunk_data, vector in zip(raw_chunks, vectors):
        point_id = str(uuid.uuid4())
        payload = {
            "document_id": str(doc.id),
            "project_id": str(doc.project_id),
            "chunk_index": chunk_data["chunk_index"],
            "source_type": doc.doc_type.value,
            "collection_name": collection_name,
            "pasal_number": chunk_data.get("pasal_number"),
            "page_number": chunk_data.get("page_number"),
            "content": chunk_data["content"][:500],  # denormalized for fast retrieval
        }
        points.append({"id": point_id, "vector": vector, "payload": payload})

        chunk_records.append(Chunk(
            document_id=doc.id,
            content=chunk_data["content"],
            chunk_index=chunk_data["chunk_index"],
            chunk_type=chunk_data["chunk_type"],
            pasal_number=chunk_data.get("pasal_number"),
            page_number=chunk_data.get("page_number"),
            qdrant_point_id=point_id,
            collection_name=collection_name,
            metadata_json=payload,
        ))

    # Upsert to Qdrant
    qc.upsert_points(collection_name, points)

    # Save to PostgreSQL
    db.add_all(chunk_records)
    await db.flush()
