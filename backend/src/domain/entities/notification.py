from datetime import datetime
from pydantic import Field
from src.domain.entities.base_entity import BaseEntity
from src.domain.enums import NotificationType, RelatedEntityType
from src.shared.constants import NOTIF_TITLE_MIN_LEN, NOTIF_TITLE_MAX_LEN, NOTIF_BODY_MAX_LEN

class Notification(BaseEntity):
    id: str | None = Field(default=None)
    recipient_id: str = Field(...)
    type: NotificationType = Field(...)
    title: str = Field(..., min_length=NOTIF_TITLE_MIN_LEN, max_length=NOTIF_TITLE_MAX_LEN)
    body: str = Field(..., max_length=NOTIF_BODY_MAX_LEN)
    related_entity_type: RelatedEntityType | None = Field(default=None)
    related_entity_id: str | None = Field(default=None)
    is_read: bool = Field(default=False)
    read_at: datetime | None = Field(default=None)
