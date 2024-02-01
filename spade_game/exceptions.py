class MessageTypeError(Exception):
    def __init__(self, message_type: str) -> None:
        message = "Message of type '{}' can not be handled.".format(message_type)
        super().__init__(message)


class UnauthorizedSenderError(Exception):
    def __init__(self, sender_jid: str) -> None:
        message = "Message received from unauthorized agent '{}'.".format(sender_jid)
        super().__init__(message)


class PlayerAlreadyConnectedError(Exception):
    def __init__(self, player_jid: str) -> None:
        message = "Player '{}' already connected in the server.".format(player_jid)
        super().__init__(message)


class PlayerNotFoundError(Exception):
    def __init__(self, player_jid: str) -> None:
        message = "Player '{}' not found in the server.".format(player_jid)
        super().__init__(message)


class InvalidContentError(Exception):
    def __init__(
        self, message_type: str, content_keys: str, expected_content_keys: str
    ):
        message = "Invalid content. Message type {} expected {} keys, but received {}.".format(
            message_type, content_keys, expected_content_keys
        )
        super().__init__(message)
