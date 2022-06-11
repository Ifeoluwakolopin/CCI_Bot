import json
from datetime import datetime


class Message:

    def __init__(self, sender:str, reciever:str, text:str, status=None, time_sent=datetime.now()) -> None:
        self.sender = sender
        self.reciever = reciever
        self.text = text
        self.status = status
        self.time_sent = time_sent

    def _get_message_json(self):
        return json.dumps({
            'sender': self.sender,
            'reciever': self.reciever,
            'message': self.text,
            'status': self.status,
            'time_sent': str(self.time_sent)
        }, indent=2)

    def update_message_status(self, update="sent"):
        self.status = update
        return f"Message status: {update}"

    def get_sender(self):
        return self.sender

    def get_reciever(self):
        return self.get_reciever
    
    def get_message(self):
        return self.text
    
    def get_content(self):
        return self._get_message_json()


class Conversation:

    def __init__(self, id:str, start_time:datetime.now(), status:str="active", ongoing:bool=True, messages:list=[]) -> None:
        self.id = id
        self.status = status
        self.ongoing = ongoing
        self.messages = []
        self.start_time = start_time

    def add_message(self, Message):
        self.messages.append(Message.get_content())
        return f"Message added to conversation by {Message.get_sender()}"

    def get_message_count(self):
        return len(self.messages)

    def update_chat_status(self, update):
        self.status = update
        return "Conversation status updated: {self.status}"

    def is_ongoing(self):
        return self.ongoing

    def get_conversation_id(self):
        return self.id

    def get_conversation_start(self):
        return self.start_time