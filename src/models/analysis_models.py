from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from src.core.config import settings


TABLE_ARGS = {"schema": settings.SCHEMA_NAME}


class AnalysisConversation(SQLModel, table=True):
    __tablename__ = "conversation"
    __table_args__ = TABLE_ARGS

    conversation_id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(
        foreign_key=f"{settings.SCHEMA_NAME}.users.user_id"
    )

    conversation_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class AnalysisMessage(SQLModel, table=True):
    __tablename__ = "message"
    __table_args__ = TABLE_ARGS

    message_id: Optional[int] = Field(default=None, primary_key=True)

    user_id: Optional[int] = Field(
        default=None,
        foreign_key=f"{settings.SCHEMA_NAME}.users.user_id",
    )

    conversation_id: int = Field(
        foreign_key=f"{settings.SCHEMA_NAME}.conversation.conversation_id"
    )

    text: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = False
    is_marked: Optional[int] = Field(default=0)


class AnalysisLog(SQLModel, table=True):
    __tablename__ = "ai_log"
    __table_args__ = TABLE_ARGS

    ai_log_id: Optional[int] = Field(default=None, primary_key=True)

    message_id: Optional[int] = Field(
        default=None,
        foreign_key=f"{settings.SCHEMA_NAME}.message.message_id",
    )

    conversation_id: int = Field(
        foreign_key=f"{settings.SCHEMA_NAME}.conversation.conversation_id"
    )

    ai_task_type: str
    output_text: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningRoute(SQLModel, table=True):
    __tablename__ = "learning_route"
    __table_args__ = TABLE_ARGS

    learning_route_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    route_text: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)