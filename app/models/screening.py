import uuid
from datetime import datetime
from sqlalchemy import (
    Integer, Boolean, String, Text, DateTime,
    Enum as SAEnum, ForeignKey, func, text
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.core.constants import ScreeningStatus, FinalResult, ScreeningStage


class ScreeningSession(Base):
    __tablename__ = "screening_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    screening_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    status: Mapped[ScreeningStatus] = mapped_column(
        SAEnum(ScreeningStatus), default=ScreeningStatus.PENDING, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    final_result: Mapped[FinalResult | None] = mapped_column(
        SAEnum(FinalResult), nullable=True
    )
    rocan_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rocan_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FormatCheckResult(Base):
    __tablename__ = "format_check_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checklist_items.id"), nullable=False
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[ScreeningStage] = mapped_column(SAEnum(ScreeningStage), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
