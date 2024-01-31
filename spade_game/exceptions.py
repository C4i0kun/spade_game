class MessageTypeError(Exception):
    def __init__(self, message_type: str) -> None:
        message = "Message of type '{}' can not be handled.".format(message_type)
        super().__init__(message)

class UnauthorizedSenderError(Exception):
    def __init__(self, sender_jid: str) -> None:
        message = "Message received from unauthorized agent '{}'.".format(sender_jid)
        super().__init__(message)

