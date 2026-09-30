import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey, JSON, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.core.constants import ChunkType


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[ChunkType] = mapped_column(SAEnum(ChunkType), nullable=False)
    pasal_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
