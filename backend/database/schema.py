"""SQLAlchemy ORM models for clinical data."""

from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, CheckConstraint
from sqlalchemy.orm import relationship

from .session import Base


class Extraction(Base):
    __tablename__ = "extractions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'QUEUED', 'PROCESSING', 'PROCESSED', 'FAILED', 'INJECTING', 'INJECTED', 'REJECTED', 'DUPLICATE')",
            name="ck_extraction_status",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    image_hash = Column(String, unique=True, index=True, nullable=True)
    semantic_hash = Column(String, index=True, nullable=True)
    filename = Column(String, nullable=False)
    raw_text = Column(Text)
    data_json = Column(Text)
    flags_json = Column(Text)
    prompt_version = Column(String, default="v1.0.0-poc")
    is_encrypted = Column(Boolean, default=False)
    status = Column(String, default="PENDING", index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    pharmacist_actions = relationship(
        "PharmacistAction", back_populates="extraction", cascade="all, delete-orphan"
    )


class PharmacistAction(Base):
    __tablename__ = "pharmacist_actions"

    action_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    extraction_id = Column(
        String,
        ForeignKey("extractions.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String, nullable=False)
    pharmacist_note = Column(Text)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    extraction = relationship("Extraction", back_populates="pharmacist_actions")
