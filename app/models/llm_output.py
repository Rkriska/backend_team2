import uuid
from datetime import datetime
from sqlalchemy import Text, DateTime, Enum as SAEnum, ForeignKey, JSON, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.core.constants import LLMClassification


class LLMOutput(Base):
    __tablename__ = "llm_outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checklist_items.id"), nullable=True
    )
    classification: Mapped[LLMClassification] = mapped_column(
        SAEnum(LLMClassification), nullable=False
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
