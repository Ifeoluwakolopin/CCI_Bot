import json
from datetime import datetime


class Message:

    def __init__(self, message_id:int, sender:str, receiver:str, text:str, status=None, time_sent=datetime.now(), reply_to=False) -> None:
        self.message_id = message_id
        self.sender = sender
        self.receiver = receiver
        self.text = text
        self.status = status
        self.time_sent = time_sent
        self.reply_to = reply_to

    def _get_message_json(self):
        return json.dumps({
            'message_id':self.message_id,
            'sender': self.sender,
            'receiver': self.receiver,
            'message': self.text,
            'status': self.status,
            'time_sent': str(self.time_sent),
            'reply_to':self.reply_to
        }, indent=2)

    def update_message_status(self, update="sent"):
        self.status = update
        return f"Message status: {update}"

    def get_sender(self):
        return self.sender

    def get_receiver(self):
        return self.get_receiver
    
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