"""
exceptions.py - Custom exception classes.

UNIT IV (Exception Handling):
  * A base class SplitterError inherits from Python's built-in Exception.
  * Each specific error is a subclass (inheritance) with its own message and
    HTTP status code.
  * Errors are raised in models/services with `raise`, and handled in app.py
    with a Flask error handler (try/except happens inside Flask for us), and
    in storage.py with explicit try / except / finally blocks.
"""


class SplitterError(Exception):
    """Base class for every error this app raises on purpose."""

    status_code = 400
    default_message = "Something went wrong."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def to_dict(self):
        # type(self).__name__ gives the class name, e.g. "RoomFullError"
        return {"error": type(self).__name__, "message": self.message}


class ValidationError(SplitterError):
    status_code = 400
    default_message = "Invalid input."


class InvalidRoomCodeError(SplitterError):
    status_code = 400
    default_message = "Room code must be exactly 6 letters or digits (e.g. A1B2C3)."


class RoomNotFoundError(SplitterError):
    status_code = 404
    default_message = "No room exists with that code."


class RoomFullError(SplitterError):
    status_code = 409
    default_message = "This room is already full."


class AlreadyPaidError(SplitterError):
    status_code = 409
    default_message = "You have already paid for this room."


class OwnerCannotJoinError(SplitterError):
    status_code = 400
    default_message = "You created this room, so your share is already paid."


class NotAMemberError(SplitterError):
    status_code = 403
    default_message = "Join the room before marking it as paid."


class StorageError(SplitterError):
    status_code = 500
    default_message = "Could not read or write the data file."
