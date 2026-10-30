import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, User

log = logging.getLogger(__name__)
BATCH = 100  # Expo accepts up to 100 messages per request


def send_push_for(db: Session, notifications: list[Notification]) -> None:
    """Best-effort Expo push for freshly created notifications. Never raises."""
    messages, owners = [], []
    for n in notifications:
        user = db.get(User, n.user_id)
        if user and user.push_token and user.push_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
            messages.append(
                {
                    "to": user.push_token,
                    "title": n.title,
                    "body": n.body,
                    "sound": "default",
                    "data": {"notification_id": n.id, "type": n.type, "group_id": n.group_id},
                }
            )
            owners.append(user)
    if not messages:
        return
    try:
        with httpx.Client(timeout=10) as client:
            for i in range(0, len(messages), BATCH):
                resp = client.post(settings.expo_push_url, json=messages[i : i + BATCH])
                resp.raise_for_status()
                tickets = resp.json().get("data", [])
                for user, ticket in zip(owners[i : i + BATCH], tickets):
                    if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                        user.push_token = None  # stale token; stop sending to it
        db.commit()
    except Exception:  # noqa: BLE001 - push is optional, in-app notifications already saved
        log.exception("Expo push send failed")
        db.rollback()
