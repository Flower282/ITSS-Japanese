from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, JSON, Text
from sqlmodel import Field, SQLModel

from src.core.config import settings


class ConversationAnalysis(SQLModel, table=True):
    __tablename__ = "conversation_analyses"
    __table_args__ = {"schema": settings.SCHEMA_NAME}

    id: int | None = Field(default=None, primary_key=True)

    meeting_title: str = Field(index=True)
    meeting_date: str | None = None
    duration_minutes: int | None = None

    transcript: str = Field(sa_column=Column(Text, nullable=False))

    understanding_score: int = 0
    overall_sentiment: str = "Trung bình"

    ai_overall_feedback: str = Field(sa_column=Column(Text, nullable=False))

    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    perception_gaps: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    decisions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    action_items: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )