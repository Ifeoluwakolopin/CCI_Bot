from datetime import datetime as dt
from enum import Enum


class Result(Enum):
    SUCCESS = "Success"
    SKIPPED = "Skipped"

    @staticmethod
    def ERROR(error_message=None):
        if error_message:
            return f"Error: {error_message}"
        else:
            return "Error"


class BotUser:
    def __init__(
        self, chat_id: int, first_name: str | None, last_name: str | None
    ) -> None:
        self.chat_id = chat_id
        self.first_name = first_name
        self.last_name = last_name
        self.date = dt.now()
        self.admin = False
        self.mute = False
        self.last_command = None
        self.active = True
        self.location = "None"
        self.birthday = "None"
        self.role = "user"

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "date": self.date,
            "admin": self.admin,
            "mute": self.mute,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "last_command": self.last_command,
            "active": self.active,
            "location": self.location,
            "birthday": self.birthday,
            "role": self.role,
        }
