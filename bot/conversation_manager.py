from datetime import datetime
from bot import db
from bson.int64 import Int64
from typing import List, Dict, Optional


class ConversationManager:

    @staticmethod
    def start_conversation(
        counselor_id: int,
        user_chat_id: int,
        request_message_id: int,
        user_name: str,
        topic: str,
    ) -> bool:
        """Start a new conversation between counselor and user"""
        try:
            # Check if conversation already exists
            existing = db.conversations.find_one(
                {
                    "counselor_id": counselor_id,
                    "user_chat_id": user_chat_id,
                    "status": "active",
                }
            )

            if existing:
                return False

            # Create new active conversation
            conversation_doc = {
                "counselor_id": Int64(counselor_id),
                "user_chat_id": Int64(user_chat_id),
                "request_message_id": request_message_id,
                "from": request_message_id,
                "status": "active",
                "created": datetime.now(),
                "last_message_time": datetime.now(),
                "user_name": user_name,
                "topic": topic,
                "messages": [],
            }

            db.conversations.insert_one(conversation_doc)

            # Update counselor mode and preserve existing last_command
            counselor = db.users.find_one({"chat_id": counselor_id})
            current_last_command = counselor.get("last_command")

            update_doc = {
                "$set": {"conversation_mode": "multi_conversation"},
                "$addToSet": {"conversations": request_message_id},
            }

            # Store pre-conversation command if counselor had one
            if current_last_command and not current_last_command.startswith(
                "in-conversation-with"
            ):
                update_doc["$set"]["pre_conversation_command"] = current_last_command
                update_doc["$set"]["last_command"] = f"in-conversation-multi"
            elif not current_last_command:
                update_doc["$set"]["last_command"] = f"in-conversation-multi"

            db.users.update_one({"chat_id": counselor_id}, update_doc)

            # Set user's conversation state (users still use single conversation model)
            db.users.update_one(
                {"chat_id": user_chat_id},
                {
                    "$set": {
                        "last_command": f"in-conversation-with={counselor_id}=pastor={request_message_id}"
                    }
                },
            )

            return True

        except Exception as e:
            print(f"Error starting conversation: {e}")
            return False

    @staticmethod
    def get_counselor_conversations(counselor_id: int) -> List[Dict]:
        """Get all active conversations for a counselor"""
        conversations = list(
            db.conversations.find(
                {"counselor_id": counselor_id, "status": "active"}
            ).sort("last_message_time", -1)
        )

        return conversations

    @staticmethod
    def end_conversation(counselor_id: int, user_chat_id: int, request_message_id: int):
        """End a specific conversation"""
        # Update conversation status
        db.conversations.update_one(
            {
                "counselor_id": counselor_id,
                "user_chat_id": user_chat_id,
                "request_message_id": request_message_id,
            },
            {"$set": {"status": "completed", "completed_at": datetime.now()}},
        )

        # Remove from counselor's active conversations
        db.users.update_one(
            {"chat_id": counselor_id},
            {"$pull": {"conversations": request_message_id}},
        )

        # Clear user's conversation state
        db.users.update_one({"chat_id": user_chat_id}, {"$set": {"last_command": None}})

        # Check if counselor has any remaining conversations
        remaining = db.conversations.count_documents(
            {"counselor_id": counselor_id, "status": "active"}
        )

        if remaining == 0:
            # No more conversations - restore pre-conversation state
            counselor = db.users.find_one({"chat_id": counselor_id})
            pre_conversation_command = counselor.get("pre_conversation_command")

            update_doc = {"$unset": {"conversation_mode": "", "conversations": ""}}

            if pre_conversation_command:
                # Restore the command they had before conversations
                update_doc["$set"] = {"last_command": pre_conversation_command}
                update_doc["$unset"]["pre_conversation_command"] = ""
            else:
                update_doc["$unset"]["last_command"] = ""

            db.users.update_one({"chat_id": counselor_id}, update_doc)

    @staticmethod
    def route_message(counselor_id: int, message_text: str) -> Optional[Dict]:
        """
        Route counselor's message to the correct user based on context
        Returns the target user info or None if routing failed
        """
        conversations = ConversationManager.get_counselor_conversations(counselor_id)

        if len(conversations) == 0:
            return None
        elif len(conversations) == 1:
            # Only one conversation, route directly
            return conversations[0]
        else:
            # Multiple conversations - need user selection interface
            return {"multiple": True, "conversations": conversations}

    @staticmethod
    def update_last_message_time(counselor_id: int, user_id: int):
        """Update the last message time for conversation sorting"""
        db.conversations.update_one(
            {"counselor_id": counselor_id, "user_id": user_id, "status": "active"},
            {"$set": {"last_message_time": datetime.now()}},
        )

    @staticmethod
    def is_counselor_in_conversation(counselor_id: int) -> bool:
        """Check if counselor is in any active conversations"""
        user = db.users.find_one({"chat_id": counselor_id})
        return user and user.get("conversation_mode") == "multi_conversation"

    @staticmethod
    def end_all_counselor_conversations(counselor_id: int):
        """End all conversations for a counselor (used by cancel command)"""
        conversations = ConversationManager.get_counselor_conversations(counselor_id)

        for conv in conversations:
            ConversationManager.end_conversation(
                counselor_id, conv["user_chat_id"], conv["request_message_id"]
            )

            # Update counseling request status
            db.counseling_requests.update_one(
                {"request_message_id": conv["request_message_id"]},
                {"$set": {"status": "completed"}},
            )

            # Update original conversation record
            db.conversations.update_one(
                {"from": conv["request_message_id"], "active": True},
                {"$set": {"active": False, "completed_at": datetime.now()}},
            )

    @staticmethod
    def get_conversation_by_request_id(request_message_id: int) -> Optional[Dict]:
        """Get conversation by request message ID"""
        return db.conversations.find_one(
            {"request_message_id": request_message_id, "status": "active"}
        )
