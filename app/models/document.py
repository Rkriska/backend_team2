import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.core.constants import DocType, DocStatus


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[DocType] = mapped_column(SAEnum(DocType), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus), default=DocStatus.PENDING, nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
