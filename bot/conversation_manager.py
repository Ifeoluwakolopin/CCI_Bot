from datetime import datetime
from typing import Any

from bot import db, logger


class ConversationManager:
    """Helpers for the live counseling conversation schema.

    The bot stores active conversations with ``active: True`` and the original
    counseling request message id in ``from``. Keep this class aligned with the
    handlers in ``chat/chat_callback_handlers.py`` to avoid competing schemas.
    """

    @staticmethod
    def start_conversation(
        counselor_id: int, counseling_request: dict[str, Any]
    ) -> bool:
        """Create an active conversation if one does not already exist."""
        request_message_id = counseling_request["request_message_id"]
        if db.conversations.find_one({"from": request_message_id, "active": True}):
            return False

        db.conversations.insert_one(
            {
                "counselor_id": counselor_id,
                "user_chat_id": counseling_request["user_chat_id"],
                "messages": [],
                "created": datetime.now(),
                "from": request_message_id,
                "last_updated": datetime.now(),
                "active": True,
            }
        )
        return True

    @staticmethod
    def get_counselor_conversations(counselor_id: int) -> list[dict[str, Any]]:
        """Get all active conversations for a counselor."""
        return list(
            db.conversations.find({"counselor_id": counselor_id, "active": True}).sort(
                "last_updated", -1
            )
        )

    @staticmethod
    def update_conversation(
        message: dict[str, Any], counselor_id: int, user_chat_id: int
    ) -> None:
        """Append a message to the active conversation transcript."""
        db.conversations.update_one(
            {
                "counselor_id": counselor_id,
                "user_chat_id": user_chat_id,
                "active": True,
            },
            {"$push": {"messages": message}, "$set": {"last_updated": datetime.now()}},
        )

    @staticmethod
    def set_conversation_status(
        counselor_id: int, user_chat_id: int, active: bool
    ) -> None:
        """Mark a conversation active/inactive using the live schema."""
        update: dict[str, Any] = {"active": active, "last_updated": datetime.now()}
        if not active:
            update["completed_at"] = datetime.now()
        db.conversations.update_one(
            {"counselor_id": counselor_id, "user_chat_id": user_chat_id},
            {"$set": update},
        )

    @staticmethod
    def end_conversation(counselor_id: int, user_chat_id: int) -> None:
        """End a specific conversation."""
        ConversationManager.set_conversation_status(counselor_id, user_chat_id, False)

    @staticmethod
    def route_message(counselor_id: int) -> dict[str, Any] | None:
        """
        Route a counselor message when only one active conversation exists.

        Returns ``{"multiple": True, "conversations": [...]}`` when the
        caller needs to ask the counselor which conversation to target.
        """
        conversations = ConversationManager.get_counselor_conversations(counselor_id)
        if len(conversations) == 0:
            return None
        if len(conversations) == 1:
            return conversations[0]
        return {"multiple": True, "conversations": conversations}

    @staticmethod
    def update_last_message_time(counselor_id: int, user_chat_id: int) -> None:
        """Update the last message time for conversation sorting."""
        db.conversations.update_one(
            {
                "counselor_id": counselor_id,
                "user_chat_id": user_chat_id,
                "active": True,
            },
            {"$set": {"last_updated": datetime.now()}},
        )

    @staticmethod
    def is_counselor_in_conversation(counselor_id: int) -> bool:
        """Check whether a counselor has any active conversations."""
        return bool(
            db.conversations.find_one({"counselor_id": counselor_id, "active": True})
        )

    @staticmethod
    def end_all_counselor_conversations(counselor_id: int) -> None:
        """End all active conversations for a counselor."""
        for conversation in ConversationManager.get_counselor_conversations(
            counselor_id
        ):
            try:
                ConversationManager.end_conversation(
                    counselor_id, conversation["user_chat_id"]
                )
                db.counseling_requests.update_one(
                    {"request_message_id": conversation["from"]},
                    {"$set": {"status": "completed"}},
                )
            except Exception:
                logger.exception(
                    "Failed to end conversation counselor_id=%s user_chat_id=%s",
                    counselor_id,
                    conversation.get("user_chat_id"),
                )

    @staticmethod
    def get_conversation_by_request_id(
        request_message_id: int,
    ) -> dict[str, Any] | None:
        """Get an active conversation by counseling request message id."""
        return db.conversations.find_one({"from": request_message_id, "active": True})
