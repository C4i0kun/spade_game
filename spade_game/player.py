import json

from spade.agent import Agent
from spade.message import Message
from spade.behaviour import FSMBehaviour, State

# State definitions
STATE_CONNECT = "STATE_INPUT"
STATE_INPUT = "STATE_OUTPUT"
STATE_ACTION = "STATE_OUTPUT"
STATE_OUTPUT = "STATE_OUTPUT"
STATE_DISCONNECT = "STATE_INPUT" # TO-DO

# Player Finite State Machine

# Player States
class Connect(State):
    async def run(self):
        body = {
            "type": "connect",
            "info": {},
        }
        msg = Message(
            to=str(self.agent.server_jid),
            sender=str(self.agent.jid),
            body=json.dumps(body),
            metadata={"performative", "inform"}
        )

        await self.send(msg)
        self.set_next_state(STATE_INPUT)

class Input(State):
    async def run(self):
        msg = await self.receive()
        if msg:
            self.agent.decode_message(msg)
            self.set_next_state(STATE_ACTION)
        else:
            self.set_next_state(STATE_INPUT)

class Action(State):
    async def run(self):
        self.agent.decide_action()
        self.set_next_state(STATE_OUTPUT)

class Output(State):
    async def run(self):
        # send message to server
        self.set_next_state(STATE_INPUT)

# Player Agent
class Player(Agent):
    def __init__(self, 
                 jid: str,
                 password: str,
                 server_jid: str,
                 verify_security: bool = False):
        super().__init__(jid, password, verify_security)
        self.server_jid = server_jid
        self.action = {}

    def decide_action(self):
        raise NotImplementedError("Subclasses must implement this")