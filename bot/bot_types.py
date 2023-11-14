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
