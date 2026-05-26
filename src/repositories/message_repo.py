from fastapi import HTTPException
from sqlmodel import Session

from src.models.analysis_models import AnalysisMessage


class MessageRepository:
    def get_by_id(self, db: Session, *, message_id: int) -> AnalysisMessage | None:
        """Returns a message by primary key."""
        return db.get(AnalysisMessage, message_id)

    def mark_message(self, db: Session, *, message_id: int) -> AnalysisMessage:
        """Sets is_marked=1 on a message (idempotent)."""
        message = self.get_by_id(db, message_id=message_id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Message not found")
        message.is_marked = 1
        db.add(message)
        db.commit()
        db.refresh(message)
        return message


message_repo = MessageRepository()
