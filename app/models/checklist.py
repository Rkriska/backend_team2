import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    checklist_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 3
    item_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # FORMAT or SUBSTANSI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
